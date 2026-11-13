import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from walkflows.multicamera_project import build_project
from walkflows.project_workflow import local_path, prepare_project


class ProjectWorkflowTest(unittest.TestCase):
    def test_windows_drive_path_is_translated_for_wsl(self):
        self.assertEqual(local_path(r"C:\Users\corli\Downloads\clip.mp4"),
                         "/mnt/c/Users/corli/Downloads/clip.mp4")

    def test_imports_matching_calibration_into_new_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); cameras=[]
            for name in ("a","b"):
                path=root/(name+".avi")
                writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"MJPG"),5,(64,48))
                if not writer.isOpened():self.skipTest("MJPG unavailable")
                for _ in range(5):writer.write(np.zeros((48,64,3),np.uint8))
                writer.release();cameras.append({"id":name,"path":str(path)})
            mapping=root/"mapping.json"
            mapping.write_text(json.dumps({"name":"old","cameras":[
                {**c,"homography":[[1,0,2],[0,1,3],[0,0,1]],
                 "calibration_polygon":[[0,0],[63,0],[63,47],[0,47]]} for c in cameras]}))
            workspace=root/"work"
            path=prepare_project("room",cameras,workspace,mapping_config=mapping)
            data=build_project(path)
            self.assertEqual(len(data["cameras"]),2)
            self.assertEqual(data["cameras"][0]["homography"][0][2],2)
            self.assertEqual(len(data["cameras"][0]["calibration_provenance"]["mapping_config_sha256"]),64)
            with self.assertRaises(FileExistsError):prepare_project("room",cameras,workspace,mapping_config=mapping)

    def test_refuses_mapping_from_different_camera(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);video=root/"a.avi"
            writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*"MJPG"),5,(64,48))
            if not writer.isOpened():self.skipTest("MJPG unavailable")
            writer.write(np.zeros((48,64,3),np.uint8));writer.release()
            mapping=root/"mapping.json"
            mapping.write_text(json.dumps({"cameras":[{"id":"other","path":str(video)}]}))
            with self.assertRaisesRegex(ValueError,"camera"):
                prepare_project("room",[{"id":"a","path":str(video)}],root/"workspace",mapping_config=mapping)


if __name__=="__main__":
    unittest.main()
