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
    def test_review_uses_decoded_frame_overlap_and_rejects_empty_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            cameras=[]; results=[]
            for cid,offset,decoded in [("a",0,20),("b",1,5)]:
                video=root/(cid+".mp4");video.write_bytes(cid.encode())
                csv=root/(cid+".csv");csv.write_text("frame,timestamp_s,local_id\n")
                cameras.append({"id":cid,"offset_seconds":offset,"homography":None,
                    "video":{"path":str(video),"sha256":file_sha256(video),"fps":5,"width":64,"height":48}})
                results.append({"id":cid,"status":"completed","decoded_frames":decoded,
                    "observations":0,"observations_sha256":file_sha256(csv),
                    "frame_count_matches_metadata":False})
            data={"status":"completed","project":{"timeline":{"start_seconds":1,"end_seconds":10},
                  "cameras":cameras},"cameras":results}
            (root/"run.json").write_text(json.dumps(data))
            server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(root))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                manifest=json.load(urllib.request.urlopen("http://127.0.0.1:"+str(server.server_port)+"/manifest.json"))
                self.assertEqual(manifest["timeline"],{"start_seconds":1,"end_seconds":2})
                self.assertFalse(manifest["cameras"][1]["frame_count_matches_metadata"])
            finally:
                server.shutdown();server.server_close();thread.join()
            cameras[1]["offset_seconds"]=5
            (root/"run.json").write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"overlap"):
                make_handler(root)

    def test_verified_assets_are_served_and_other_files_are_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "clip.mp4"
            video.write_bytes(b"0123456789")
            (root / "a.csv").write_text("frame,timestamp_s,local_id,left,top,right,bottom\n0,0,1,1,2,3,4\n")
            data = {"status": "completed", "scope": "unverified", "project": {
                "name": "test", "timeline": {"start_seconds": 0, "end_seconds": 1},
                "cameras": [{"id": "a", "offset_seconds": 0, "homography": None,
                             "normalization": {"source_sha256": "a"*64, "output_sha256": file_sha256(video), "manifest_sha256": "b"*64, "ffmpeg_sha256": "c"*64, "requested_fps": 5},
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
                self.assertEqual(manifest["provenance"]["source_videos"][0]["normalization"]["source_sha256"],"a"*64)
                self.assertTrue(manifest["cameras"][0]["normalized_analysis_input"])
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
                revision=manifest["cameras"][0]["observations_revision"]
                req=urllib.request.Request(base + "/observations/a?v=" + revision,
                    headers={"If-Modified-Since":"Wed, 21 Oct 2099 07:28:00 GMT"})
                with urllib.request.urlopen(req) as response:
                    self.assertEqual(response.status,200)
                    self.assertIn("no-store",response.headers.get("Cache-Control",""))
                    self.assertIn(b"0,0,1",response.read())
                with self.assertRaises(urllib.error.HTTPError) as stale:
                    urllib.request.urlopen(base + "/observations/a?v=incorrect")
                self.assertEqual(stale.exception.code,409)
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
                "offset_seconds":0.3,"video": {"path": str(video), "sha256": file_sha256(video), "width": 64, "height": 48, "duration_seconds":2}}]}
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_calibration_handler(project))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = "http://127.0.0.1:" + str(server.server_port)
            try:
                data = json.load(urllib.request.urlopen(base + "/manifest.json"))
                self.assertEqual(data["cameras"][0]["id"], "front")
                self.assertEqual(data["cameras"][0]["offset_seconds"], 0.3)
                self.assertEqual(data["cameras"][0]["duration_seconds"], 2)
                with urllib.request.urlopen(base + "/sync") as response:
                    self.assertEqual(response.status, 200)
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
