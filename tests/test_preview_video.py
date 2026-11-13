import csv
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from walkflows.multicamera_project import build_project
from walkflows.multicamera_processing import file_sha256
from walkflows.multicamera_preview import build_preview_bundle, build_project_preview_bundle
from walkflows.multicamera_review import make_handler, make_calibration_handler


class PreviewVideoTest(unittest.TestCase):
    def test_transcodes_without_modifying_source_and_detects_tampering(self):
        if not shutil.which("ffmpeg") and importlib.util.find_spec("imageio_ffmpeg") is None:
            self.skipTest("optional FFmpeg not installed")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);video=root/"source.avi"
            writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*"MJPG"),5,(64,48))
            if not writer.isOpened():self.skipTest("MJPG unavailable")
            for i in range(8):writer.write(np.full((48,64,3),i*25,np.uint8))
            writer.release()
            config=root/"project.json"
            config.write_text(json.dumps({"cameras":[{"id":"a","path":"source.avi"}]}))
            project=build_project(config)
            run=root/"run";run.mkdir()
            csvpath=run/"a.csv"
            csvpath.write_text("frame,timestamp_s,local_id,left,top,right,bottom\n",encoding="utf-8")
            state={"status":"completed","project":project,"model":{},
                   "cameras":[{"id":"a","status":"completed","decoded_frames":8,"observations":0,
                                "observations_sha256":file_sha256(csvpath)}]}
            (run/"run.json").write_text(json.dumps(state))
            original=file_sha256(video);dest=root/"preview"
            result=build_preview_bundle(run,dest)
            self.assertEqual(file_sha256(video),original)
            self.assertEqual(result["cameras"][0]["decoded_frames"],8)
            self.assertEqual(result["cameras"][0]["source_sha256"],original)
            self.assertTrue((dest/"a.mp4").is_file())
            make_handler(run,preview_dir=dest)
            with self.assertRaises(FileExistsError):build_preview_bundle(run,dest)
            (dest/"a.mp4").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError,"hash"):make_handler(run,preview_dir=dest)

    def test_previews_from_project_work_before_and_after_processing(self):
        if not shutil.which("ffmpeg") and importlib.util.find_spec("imageio_ffmpeg") is None:
            self.skipTest("optional FFmpeg not installed")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);video=root/"source.avi"
            writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*"MJPG"),5,(64,48))
            if not writer.isOpened():self.skipTest("MJPG unavailable")
            for i in range(4):writer.write(np.full((48,64,3),i*20,np.uint8))
            writer.release()
            config=root/"project.json"
            config.write_text(json.dumps({"name":"room","cameras":[{"id":"a","path":"source.avi"}]}))
            project=build_project(config);preview=root/"preview"
            result=build_project_preview_bundle(config,preview)
            self.assertEqual(result["kind"],"project")
            self.assertEqual(result["cameras"][0]["decoded_frames"],4)
            make_calibration_handler(project,preview_dir=preview)
            statepath=preview/"state.json"
            state=json.loads(statepath.read_text())
            statepath.write_text(json.dumps({"status":"failed"}))
            with self.assertRaisesRegex(ValueError,"incomplete"):
                make_calibration_handler(project,preview_dir=preview)
            statepath.write_text(json.dumps(state))
            run=root/"run";run.mkdir();csvpath=run/"a.csv"
            csvpath.write_text("frame,timestamp_s,local_id,left,top,right,bottom\n")
            state={"status":"completed","project":project,"model":{},"cameras":[
                {"id":"a","status":"completed","decoded_frames":4,"observations":0,
                 "observations_sha256":file_sha256(csvpath)}]}
            (run/"run.json").write_text(json.dumps(state))
            make_handler(run,preview_dir=preview)
            (preview/"a.mp4").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError,"hash"):
                make_calibration_handler(project,preview_dir=preview)
