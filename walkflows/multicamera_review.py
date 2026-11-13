"""Serve a completed generic run on loopback with explicit file allowlisting."""
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from walkflows.multicamera_processing import file_sha256
from walkflows.review_server import RangeHandler

WEB = Path(__file__).resolve().parent / "web"


def make_handler(directory):
    directory = Path(directory).resolve(strict=True)
    run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    if run.get("status") != "completed":
        raise ValueError("only completed runs can be reviewed")
    sources = run["project"]["cameras"]
    results = {x["id"]: x for x in run["cameras"]}
    if len(results) != len(sources):
        raise ValueError("incomplete camera results")
    paths = {"/": WEB / "index.html", "/app.js": WEB / "app.js", "/analytics.js": WEB / "analytics.js", "/style.css": WEB / "style.css"}
    cameras = []
    for camera in sources:
        cid = camera["id"]
        if not isinstance(cid, str) or not cid or not all(ch.isascii() and (ch.isalnum() or ch in "_-") for ch in cid):
            raise ValueError("invalid camera id")
        info = results.get(cid)
        if not info or info.get("status") != "completed":
            raise ValueError("incomplete camera " + cid)
        video = Path(camera["video"]["path"]).resolve(strict=True)
        csv_path = directory / (cid + ".csv")
        if file_sha256(video) != camera["video"]["sha256"] or file_sha256(csv_path) != info["observations_sha256"]:
            raise ValueError("asset hash mismatch: " + cid)
        paths["/video/" + cid] = video
        paths["/observations/" + cid] = csv_path
        cameras.append({"id": cid, "offset_seconds": camera["offset_seconds"],
                        "fps": camera["video"]["fps"], "width": camera["video"]["width"],
                        "height": camera["video"]["height"], "calibrated": camera["homography"] is not None,
                        "frames": info["decoded_frames"], "observations": info["observations"],
                        "frame_count_matches_metadata": info.get("frame_count_matches_metadata")})
    provenance = {"source_videos": [
        {"id": c["id"], "sha256": c["video"]["sha256"], "offset_seconds": c["offset_seconds"],
         "homography": c.get("homography"), "calibration_polygon": c.get("calibration_polygon"),
         "analysis_roi": c.get("analysis_roi"),
         "observations_sha256": results[c["id"]]["observations_sha256"]} for c in sources],
        "model": {k: run.get("model", {}).get(k) for k in ("sha256", "tracker", "confidence", "device")},
        "versions": run.get("versions", {}), "scope": run.get("scope", "")}
    manifest = json.dumps({"name": run["project"].get("name", "WalkFlows"),
                           "timeline": run["project"]["timeline"], "scope": run.get("scope", ""),
                           "provenance": provenance, "cameras": cameras}, ensure_ascii=False).encode("utf-8")

    class Handler(RangeHandler):
        def translate_path(self, path):
            return str(paths.get(urlsplit(path).path, WEB / "__not_found__"))

        def send_head(self):
            route = urlsplit(self.path).path
            if route == "/manifest.json":
                from io import BytesIO
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(manifest)))
                self.end_headers()
                self._byte_count = None
                return BytesIO(manifest)
            if route not in paths:
                self.send_error(404)
                return None
            return super().send_head()

    return Handler


def serve(directory, port):
    handler = make_handler(directory)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"WalkFlows review: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def make_calibration_handler(project):
    """Expose only project videos and a sanitized calibration interface."""
    paths = {"/": WEB / "calibrate.html", "/calibrate.js": WEB / "calibrate.js",
             "/sync": WEB / "sync.html", "/sync.js": WEB / "sync.js", "/style.css": WEB / "style.css"}
    cameras = []
    seen = set()
    for camera in project["cameras"]:
        cid = camera["id"]
        if (not isinstance(cid, str) or not cid or cid in seen or
                not all(ch.isascii() and (ch.isalnum() or ch in "_-") for ch in cid)):
            raise ValueError("invalid camera id")
        seen.add(cid)
        video = Path(camera["video"]["path"]).resolve(strict=True)
        if file_sha256(video) != camera["video"]["sha256"]:
            raise ValueError("video hash mismatch: " + cid)
        paths["/video/" + cid] = video
        cameras.append({"id": cid, "width": camera["video"]["width"],
                        "height": camera["video"]["height"],
                        "offset_seconds": camera["offset_seconds"],
                        "duration_seconds": camera["video"]["duration_seconds"]})
    manifest = json.dumps({"name": project.get("name", "WalkFlows"), "cameras": cameras},
                          ensure_ascii=False).encode("utf-8")

    class CalibrationHandler(RangeHandler):
        def translate_path(self, path):
            return str(paths.get(urlsplit(path).path, WEB / "__not_found__"))

        def send_head(self):
            route = urlsplit(self.path).path
            if route == "/manifest.json":
                from io import BytesIO
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(manifest)))
                self.end_headers()
                self._byte_count = None
                return BytesIO(manifest)
            if route not in paths:
                self.send_error(404)
                return None
            return super().send_head()

    return CalibrationHandler


def serve_calibration(project, port):
    server = ThreadingHTTPServer(("127.0.0.1", port), make_calibration_handler(project))
    print(f"WalkFlows calibration: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
