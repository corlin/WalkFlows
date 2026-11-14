import unittest
import cv2
import numpy as np

from walkflows.ground_matching import suggest_ground_matches

class GroundMatchingTest(unittest.TestCase):
    def test_matches_common_plane_and_preserves_coordinate_direction(self):
        rng=np.random.default_rng(18)
        image=rng.integers(0,256,(360,480),dtype=np.uint8)
        transform=np.float32([[1,0,12],[0,1,8]])
        shifted=cv2.warpAffine(image,transform,(480,360))
        polygon=[[30,30],[440,30],[440,320],[30,320]]
        result=suggest_ground_matches(image,shifted,polygon,polygon)
        self.assertEqual(result["status"],"candidates")
        self.assertGreaterEqual(len(result["matches"]),4)
        for pair in result["matches"]:
            x,y=pair["reference"];u,v=pair["target"]
            self.assertAlmostEqual(u-x,12,delta=2)
            self.assertAlmostEqual(v-y,8,delta=2)

    def test_local_endpoint_returns_candidates_and_rejects_cross_origin(self):
        import json
        import tempfile
        import threading
        import urllib.error
        import urllib.request
        from http.server import ThreadingHTTPServer
        from pathlib import Path
        from walkflows.multicamera_project import build_project
        from walkflows.multicamera_review import make_calibration_handler

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rng=np.random.default_rng(23)
            frame=rng.integers(0,256,(240,320,3),dtype=np.uint8)
            cameras=[]
            for cid,im in (("a",frame),("b",cv2.warpAffine(frame,np.float32([[1,0,7],[0,1,5]]),(320,240)))):
                path=root/(cid+".avi")
                writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"MJPG"),5,(320,240))
                if not writer.isOpened():self.skipTest("MJPG unavailable")
                for _ in range(3):writer.write(im)
                writer.release();cameras.append({"id":cid,"path":str(path)})
            config=root/"project.json";config.write_text(json.dumps({"name":"demo","cameras":cameras}))
            server=ThreadingHTTPServer(("127.0.0.1",0),make_calibration_handler(build_project(config)))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base="http://127.0.0.1:"+str(server.server_port)
            payload={"reference":"a","target":"b","reference_frame":0,"target_frame":0,
                "reference_polygon":[[10,10],[300,10],[300,220],[10,220]],
                "target_polygon":[[10,10],[300,10],[300,220],[10,220]],
                "reference_points":[],"plane_points":[]}
            body=json.dumps(payload).encode()
            try:
                request=urllib.request.Request(base+"/ground-match",data=body,headers={"Content-Type":"application/json","Origin":base})
                with urllib.request.urlopen(request) as response: result=json.load(response)
                self.assertEqual(result["status"],"candidates")
                self.assertEqual(result["plane_mode"],"reference_image")
                self.assertGreaterEqual(len(result["matches"]),4)
                np.testing.assert_allclose(result["matches"][0]["plane"],result["matches"][0]["reference"],atol=1e-6)
                request=urllib.request.Request(base+"/ground-match",data=body,headers={"Origin":"http://example.org"})
                with self.assertRaises(urllib.error.HTTPError) as bad:urllib.request.urlopen(request)
                self.assertEqual(bad.exception.code,403)
            finally:server.shutdown();server.server_close();thread.join()

    def test_blank_and_invalid_masks_fail_closed(self):
        blank=np.zeros((200,200),np.uint8)
        poly=[[0,0],[199,0],[199,199],[0,199]]
        self.assertEqual(suggest_ground_matches(blank,blank,poly,poly)["status"],"insufficient_features")
        with self.assertRaises(ValueError):
            suggest_ground_matches(blank,blank,[[0,0],[1,1]],poly)
