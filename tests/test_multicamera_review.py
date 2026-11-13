import csv
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from walkflows.multicamera_processing import file_sha256
from walkflows.multicamera_review import make_handler, make_calibration_handler


class ReviewTest(unittest.TestCase):
    def test_verified_assets_are_served_and_other_files_are_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "clip.mp4"
            video.write_bytes(b"0123456789")
            (root / "a.csv").write_text("frame,timestamp_s,local_id,left,top,right,bottom\n0,0,1,1,2,3,4\n")
            data = {"status": "completed", "scope": "unverified", "project": {
                "name": "test", "timeline": {"start_seconds": 0, "end_seconds": 1},
                "cameras": [{"id": "a", "offset_seconds": 0, "homography": None,
                             "video": {"path": str(video), "sha256": file_sha256(video),
                                       "fps": 5, "width": 64, "height": 48}}]},
                "cameras": [{"id": "a", "status": "completed", "decoded_frames": 5,
                             "observations": 1, "observations_sha256": file_sha256(root / "a.csv")}]}
            (root / "run.json").write_text(json.dumps(data))
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = "http://127.0.0.1:" + str(server.server_port)
            try:
                manifest = json.load(urllib.request.urlopen(base + "/manifest.json"))
                self.assertNotIn(str(root), json.dumps(manifest))
                self.assertEqual(manifest["provenance"]["source_videos"][0]["sha256"], file_sha256(video))
                self.assertEqual(manifest["provenance"]["source_videos"][0]["observations_sha256"], file_sha256(root / "a.csv"))
                with urllib.request.urlopen(base + "/video/a?cache=1") as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers.get_content_type(), "video/mp4")
                    self.assertEqual(response.read(), b"0123456789")
                with self.assertRaises(urllib.error.HTTPError) as missing:
                    urllib.request.urlopen(base + "/video/unknown")
                self.assertEqual(missing.exception.code, 404)
                request = urllib.request.Request(base + "/video/a", headers={"Range": "bytes=2-4"})
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.read(), b"234")
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(base + "/run.json")
                (root / "a.csv").write_text("changed")
                with self.assertRaisesRegex(ValueError, "hash"):
                    make_handler(root)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_calibration_server_exposes_only_declared_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"0123456789")
            project = {"name": "test", "cameras": [{"id": "front",
                "video": {"path": str(video), "sha256": file_sha256(video), "width": 64, "height": 48}}]}
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_calibration_handler(project))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = "http://127.0.0.1:" + str(server.server_port)
            try:
                data = json.load(urllib.request.urlopen(base + "/manifest.json"))
                self.assertEqual(data["cameras"][0]["id"], "front")
                self.assertNotIn(str(video), json.dumps(data))
                with urllib.request.urlopen(base + "/video/front") as response:
                    self.assertEqual(response.read(), b"0123456789")
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(base + "/run.json")
                video.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "hash"):
                    make_calibration_handler(project)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
