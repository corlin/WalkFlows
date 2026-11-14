import unittest
import cv2
import numpy as np

from walkflows.ground_matching import suggest_ground_matches, alignment_preview

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

    def test_textured_background_does_not_starve_marked_region(self):
        rng=np.random.default_rng(501)
        image=rng.integers(0,256,(900,1600),np.uint8)
        x,y,w,h=400,250,340,260
        patch=rng.integers(0,256,(h,w),np.uint8)
        image[y:y+h,x:x+w]=cv2.GaussianBlur(patch,(7,7),1.5)
        shifted=cv2.warpAffine(image,np.float32([[1,0,10],[0,1,7]]),(1600,900))
        polygon=[[x,y],[x+w-1,y],[x+w-1,y+h-1],[x,y+h-1]]
        result=suggest_ground_matches(image,shifted,polygon,polygon)
        self.assertEqual(result["status"],"candidates")
        self.assertGreaterEqual(len(result["matches"]),4)
        for pair in result["matches"]:
            self.assertAlmostEqual(pair["target"][0]-pair["reference"][0],10,delta=2)
            self.assertAlmostEqual(pair["target"][1]-pair["reference"][1],7,delta=2)

    def test_fallback_is_used_only_when_primary_has_no_candidates(self):
        from unittest.mock import patch
        blank=np.zeros((64,64),np.uint8)
        polygon=[[0,0],[63,0],[63,63],[0,63]]
        with patch("walkflows.ground_matching._suggest_sift",return_value={"status":"insufficient_inliers"}) as primary, \
             patch("walkflows.ground_matching._suggest_xfeat",return_value={"status":"candidates","algorithm":"xfeat"}) as fallback:
            result=suggest_ground_matches(blank,blank,polygon,polygon)
            self.assertEqual(result["algorithm"],"xfeat")
            self.assertEqual(result["sift_status"],"insufficient_inliers")
            fallback.assert_called_once()
        with patch("walkflows.ground_matching._suggest_sift",return_value={"status":"candidates"}) as primary, \
             patch("walkflows.ground_matching._suggest_xfeat") as fallback:
            self.assertEqual(suggest_ground_matches(blank,blank,polygon,polygon)["algorithm"],"sift")
            fallback.assert_not_called()

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
                self.assertEqual(result["alignment_preview"]["status"],"preview")
                np.testing.assert_allclose(result["matches"][0]["plane"],result["matches"][0]["reference"],atol=1e-6)
                request=urllib.request.Request(base+"/ground-match",data=body,headers={"Origin":"http://example.org"})
                with self.assertRaises(urllib.error.HTTPError) as bad:urllib.request.urlopen(request)
                self.assertEqual(bad.exception.code,403)
            finally:server.shutdown();server.server_close();thread.join()

    def test_alignment_preview_maps_target_polygon_to_reference(self):
        pairs=[{"reference":[x,y],"target":[x+12,y+8]} for x,y in [(10,10),(180,10),(180,150),(10,150),(80,70),(130,110),(40,90),(150,60)]]
        polygon=[[22,18],[192,18],[192,158],[22,158]]
        result=alignment_preview(pairs,polygon,(200,240))
        self.assertEqual(result["status"],"preview")
        np.testing.assert_allclose(result["target_in_reference"],[[10,10],[180,10],[180,150],[10,150]],atol=1e-4)

    def test_blank_and_invalid_masks_fail_closed(self):
        blank=np.zeros((200,200),np.uint8)
        poly=[[0,0],[199,0],[199,199],[0,199]]
        self.assertEqual(suggest_ground_matches(blank,blank,poly,poly)["status"],"insufficient_features")
        with self.assertRaises(ValueError):
            suggest_ground_matches(blank,blank,[[0,0],[1,1]],poly)
