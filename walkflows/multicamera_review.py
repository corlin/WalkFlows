"""Serve a completed generic run on loopback with explicit file allowlisting."""
import json
import math
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from walkflows.multicamera_processing import file_sha256
from walkflows.review_server import RangeHandler

WEB = Path(__file__).resolve().parent / "web"


def _revision_matches(path, route, revisions):
    query = parse_qs(urlsplit(path).query, keep_blank_values=True)
    return route not in revisions or "v" not in query or query["v"] == [revisions[route]]



def _load_previews(preview_dir, sources, *, run_sha=None):
    if preview_dir is None:
        return None, {}
    root = Path(preview_dir).resolve(strict=True)
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    if state.get("status") != "completed":
        raise ValueError("preview bundle is incomplete")
    index = json.loads((root / "preview.json").read_text(encoding="utf-8"))
    kind = index.get("kind", "run")
    if index.get("schema_version") != 1 or kind not in ("run", "project"):
        raise ValueError("invalid preview manifest")
    if kind == "run" and run_sha is not None and index.get("run_sha256") != run_sha:
        raise ValueError("preview run hash mismatch")
    entries = index.get("cameras")
    if not isinstance(entries, list):
        raise ValueError("invalid preview manifest")
    previews = {item["id"]: item for item in entries}
    if len(previews) != len(entries) or set(previews) - {c["id"] for c in sources}:
        raise ValueError("invalid preview camera selection")
    return root, previews


def _preview_path(root, preview, camera, expected_frames=None):
    cid = camera["id"]
    path = (root / (cid + ".mp4")).resolve(strict=True)
    source = camera["video"]
    if (not path.is_relative_to(root) or preview["source_sha256"] != source["sha256"] or
            preview["width"] != source["width"] or preview["height"] != source["height"] or
            not isinstance(preview["fps"], (int, float)) or
            not math.isclose(preview["fps"], source["fps"], rel_tol=0.001, abs_tol=0.001) or
            type(preview["decoded_frames"]) is not int or preview["decoded_frames"] <= 0 or
            (expected_frames is not None and preview["decoded_frames"] != expected_frames) or
            file_sha256(path) != preview["preview_sha256"]):
        raise ValueError("preview hash, dimensions or frame count mismatch: " + cid)
    return path


def make_handler(directory, preview_dir=None):
    directory = Path(directory).resolve(strict=True)
    run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    if run.get("status") != "completed":
        raise ValueError("only completed runs can be reviewed")
    sources = run["project"]["cameras"]
    results = {x["id"]: x for x in run["cameras"]}
    if len(results) != len(sources):
        raise ValueError("incomplete camera results")
    paths = {"/": WEB / "index.html", "/app.js": WEB / "app.js", "/analytics.js": WEB / "analytics.js", "/style.css": WEB / "style.css"}
    preview_root, previews = _load_previews(preview_dir, sources, run_sha=file_sha256(directory / "run.json"))
    revisions = {}
    cameras = []
    for camera in sources:
        cid = camera["id"]
        if not isinstance(cid, str) or not cid or not all(ch.isascii() and (ch.isalnum() or ch in "_-") for ch in cid):
            raise ValueError("invalid camera id")
        info = results.get(cid)
        if not info or info.get("status") != "completed":
            raise ValueError("incomplete camera " + cid)
        fps = camera["video"]["fps"]
        offset = camera["offset_seconds"]
        decoded = info.get("decoded_frames")
        if (type(decoded) is not int or decoded <= 0 or
                isinstance(fps, bool) or not isinstance(fps, (int, float)) or not math.isfinite(fps) or fps <= 0 or
                isinstance(offset, bool) or not isinstance(offset, (int, float)) or not math.isfinite(offset)):
            raise ValueError("invalid decoded timeline: " + cid)
        video = Path(camera["video"]["path"]).resolve(strict=True)
        csv_path = directory / (cid + ".csv")
        if file_sha256(video) != camera["video"]["sha256"] or file_sha256(csv_path) != info["observations_sha256"]:
            raise ValueError("asset hash mismatch: " + cid)
        preview = previews.get(cid)
        playback = video
        if preview:
            playback = _preview_path(preview_root, preview, camera, expected_frames=info["decoded_frames"])
        paths["/video/" + cid] = playback
        paths["/observations/" + cid] = csv_path
        video_revision = preview["preview_sha256"] if preview else camera["video"]["sha256"]
        revisions["/video/" + cid] = video_revision
        revisions["/observations/" + cid] = info["observations_sha256"]
        cameras.append({"id": cid, "offset_seconds": camera["offset_seconds"],
                        "video_revision": video_revision, "observations_revision": info["observations_sha256"],
                        "video_source": "transcoded_preview" if preview else "original",
                        "fps": camera["video"]["fps"], "width": camera["video"]["width"],
                        "height": camera["video"]["height"], "codec_fourcc": camera["video"].get("codec_fourcc"),
                        "calibrated": camera["homography"] is not None,
                        "normalized_analysis_input":bool(camera.get("normalization")),
                        "frames": info["decoded_frames"], "observations": info["observations"],
                        "frame_count_matches_metadata": info.get("frame_count_matches_metadata")})
    if not cameras:
        raise ValueError("no camera results")
    timeline = {"start_seconds": max(c["offset_seconds"] for c in cameras),
                "end_seconds": min(c["offset_seconds"] + c["frames"] / c["fps"] for c in cameras)}
    if timeline["end_seconds"] <= timeline["start_seconds"]:
        raise ValueError("decoded videos have no temporal overlap")
    provenance = {"source_videos": [
        {"id": c["id"], "sha256": c["video"]["sha256"], "offset_seconds": c["offset_seconds"],
         "homography": c.get("homography"), "calibration_polygon": c.get("calibration_polygon"),
         "analysis_roi": c.get("analysis_roi"),
         "normalization": ({k:c["normalization"].get(k) for k in ("source_sha256","output_sha256","manifest_sha256","ffmpeg_sha256","requested_fps")} if c.get("normalization") else None),
         "observations_sha256": results[c["id"]]["observations_sha256"]} for c in sources],
        "model": {k: run.get("model", {}).get(k) for k in ("sha256", "tracker", "confidence", "device", "image_size")},
        "versions": run.get("versions", {}), "scope": run.get("scope", ""),
        "playback_previews": [{"id":cid,"preview_sha256":item["preview_sha256"]} for cid,item in previews.items()]}
    manifest = json.dumps({"name": run["project"].get("name", "WalkFlows"),
                           "timeline": timeline, "scope": run.get("scope", ""),
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
            if not _revision_matches(self.path, route, revisions):
                self.send_error(409, "Asset revision changed; reload the project")
                return None
            return super().send_head()

    return Handler


def serve(directory, port, preview_dir=None):
    handler = make_handler(directory, preview_dir=preview_dir)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"WalkFlows review: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def make_calibration_handler(project, preview_dir=None):
    """Expose only project videos and a sanitized calibration interface."""
    paths = {"/": WEB / "calibrate.html", "/calibrate.js": WEB / "calibrate.js",
             "/sync": WEB / "sync.html", "/sync.js": WEB / "sync.js", "/style.css": WEB / "style.css"}
    cameras = []
    revisions = {}
    preview_root, previews = _load_previews(preview_dir, project["cameras"])
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
        preview = previews.get(cid)
        playback = _preview_path(preview_root, preview, camera) if preview else video
        revision = preview["preview_sha256"] if preview else camera["video"]["sha256"]
        paths["/video/" + cid] = playback
        revisions["/video/" + cid] = revision
        cameras.append({"id": cid, "video_revision": revision,
                        "video_source": "transcoded_preview" if preview else "original",
                        "normalized_analysis_input":bool(camera.get("normalization")),
                        "width": camera["video"]["width"],
                        "height": camera["video"]["height"],
                        "offset_seconds": camera["offset_seconds"],
                        "duration_seconds": camera["video"]["duration_seconds"],
                        "codec_fourcc": camera["video"].get("codec_fourcc")})
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
            if not _revision_matches(self.path, route, revisions):
                self.send_error(409, "Asset revision changed; reload the project")
                return None
            return super().send_head()

    return CalibrationHandler


def serve_calibration(project, port, preview_dir=None):
    server = ThreadingHTTPServer(("127.0.0.1", port), make_calibration_handler(project, preview_dir=preview_dir))
    print(f"WalkFlows calibration: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
