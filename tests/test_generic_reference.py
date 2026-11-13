import csv
import json
import tempfile
import unittest
from pathlib import Path

from walkflows.generic_reference import evaluate_run
from walkflows.multicamera_processing import file_sha256


class GenericReferenceTest(unittest.TestCase):
    def test_conditional_matching_and_alignment_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            video=root/"video.mp4";video.write_bytes(b"video")
            csv_path=root/"front.csv"
            with csv_path.open("w",newline="") as handle:
                w=csv.DictWriter(handle,fieldnames=["frame","local_id","world_x","world_y"])
                w.writeheader();w.writerows([
                    {"frame":0,"local_id":1,"world_x":1.1,"world_y":1},
                    {"frame":1,"local_id":1,"world_x":"","world_y":""},
                    {"frame":1,"local_id":2,"world_x":9,"world_y":9}])
            run={"status":"completed","project":{"cameras":[{"id":"front","offset_seconds":0,
                "video":{"path":str(video),"sha256":file_sha256(video),"fps":5}}]},
                "cameras":[{"id":"front","status":"completed","decoded_frames":2,
                            "observations_sha256":file_sha256(csv_path)}]}
            (root/"run.json").write_text(json.dumps(run))
            ref={"track_results":{"frames":2,"width":10,"height":10,"hist-sz":1,"top-left":[0,0],
                "frame-duration":0.2,"start-frame":0,"tracks":[{"id":4,"path":[[1,1,0],[1,1,1]]}]}}
            ref_path=root/"reference.json";ref_path.write_text(json.dumps(ref))
            report=evaluate_run(root,ref_path,0.5)
            camera=report["cameras"][0]
            self.assertEqual(camera["projected_observations"],2)
            self.assertEqual(camera["matched_observations"],1)
            self.assertAlmostEqual(camera["median_matched_distance"],0.1)
            run["project"]["cameras"][0]["offset_seconds"]=1
            (root/"run.json").write_text(json.dumps(run))
            with self.assertRaisesRegex(ValueError,"alignment"):
                evaluate_run(root,ref_path,0.5)
            csv_path.write_text("changed")
            run["project"]["cameras"][0]["offset_seconds"]=0
            (root/"run.json").write_text(json.dumps(run))
            with self.assertRaisesRegex(ValueError,"hash"):
                evaluate_run(root,ref_path,0.5)
