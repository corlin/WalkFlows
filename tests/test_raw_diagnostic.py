import unittest
from walkflows.raw_diagnostic import summarize_raw


class RawDiagnosticTest(unittest.TestCase):
    def test_counts_low_and_high_nearby_detections_by_frame(self):
        camera={"id":"a","offset_seconds":0,"homography":[[1,0,0],[0,1,0],[0,0,1]],
                "calibration_polygon":[[0,0],[10,0],[10,10],[0,10]],"video":{"fps":5}}
        probe={"confidence":0.1,"project":{"cameras":[camera]},"results":[
            {"camera":"a","frame":0,"weight_sha256":"w","detections":[
                {"box":[0.5,0,1.5,1],"confidence":0.2},
                {"box":[0.5,0,1.5,1],"confidence":0.3}]},
            {"camera":"a","frame":1,"weight_sha256":"w","detections":[]}]}
        reference={"frames":2,"width":10,"height":10,"hist-sz":1,"top-left":[0,0],
            "frame-duration":0.2,"start-frame":0,"tracks":[{"id":7,"path":[[1,1,0],[1,1,1]]}]}
        out=summarize_raw(probe,reference,7,0.5,0.25)
        self.assertEqual(out["frames_with_near_detection"],1)
        self.assertEqual(out["frames_with_high_near_detection"],1)
        self.assertEqual(len(out["near_detections"]),2)
        probe["project"]["cameras"][0]["offset_seconds"]=1
        with self.assertRaisesRegex(ValueError,"alignment"): summarize_raw(probe,reference,7,0.5,0.25)
