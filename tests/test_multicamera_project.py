import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from walkflows.multicamera_project import build_project, create_config


class MulticameraProjectTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ("one.avi", "two.avi"):
            writer = cv2.VideoWriter(str(self.root / name),
                                     cv2.VideoWriter_fourcc(*"MJPG"), 5.0, (64, 48))
            if not writer.isOpened():
                self.skipTest("OpenCV MJPG video writer unavailable")
            for i in range(5):
                writer.write(np.full((48, 64, 3), i * 30, np.uint8))
            writer.release()
        self.config = self.root / "project.json"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, cameras):
        self.config.write_text(json.dumps({"name": "Room", "cameras": cameras}))

    def test_relative_files_metadata_hash_and_overlapping_timeline(self):
        self.write([{"id": "front", "path": "one.avi", "offset_seconds": 0},
                    {"id": "back", "path": "two.avi", "offset_seconds": 0.2,
                     "homography": [[1, 0, 2], [0, 1, 3], [0, 0, 1]]}])
        result = build_project(self.config)
        self.assertEqual(result["timeline"]["start_seconds"], 0.2)
        self.assertAlmostEqual(result["timeline"]["end_seconds"], 1.0)
        self.assertEqual(result["cameras"][0]["video"]["frame_count"], 5)
        self.assertEqual(result["cameras"][0]["video"]["width"], 64)
        self.assertEqual(len(result["cameras"][0]["video"]["sha256"]), 64)
        self.assertIsNone(result["cameras"][0]["homography"])
        self.assertEqual(result["cameras"][1]["homography"][0][2], 2.0)

    def test_duplicate_camera_and_nonoverlapping_time_rejected(self):
        self.write([{"id": "same", "path": "one.avi"},
                    {"id": "same", "path": "two.avi"}])
        with self.assertRaisesRegex(ValueError, "camera"):
            build_project(self.config)
        self.write([{"id": "one", "path": "one.avi"},
                    {"id": "two", "path": "two.avi", "offset_seconds": 2}])
        with self.assertRaisesRegex(ValueError, "overlap"):
            build_project(self.config)

    def test_bad_video_and_singular_homography_rejected(self):
        (self.root / "broken.mp4").write_text("not a video")
        self.write([{"id": "bad", "path": "broken.mp4"}])
        with self.assertRaisesRegex(ValueError, "video"):
            build_project(self.config)
        self.write([{"id": "bad", "path": "one.avi",
                     "homography": [[1, 0, 0], [0, 0, 0], [0, 0, 1]]}])
        with self.assertRaisesRegex(ValueError, "homography"):
            build_project(self.config)

    def test_calibration_polygon_is_validated_and_preserved(self):
        self.write([{"id": "one", "path": "one.avi", "homography": [[1,0,0],[0,1,0],[0,0,1]],
                     "calibration_polygon": [[0,0],[31,0],[31,47],[0,47]]}])
        result = build_project(self.config)
        self.assertEqual(result["cameras"][0]["calibration_polygon"][1], [31.0, 0.0])
        self.write([{"id": "one", "path": "one.avi", "homography": [[1,0,0],[0,1,0],[0,0,1]],
                     "calibration_polygon": [[0,0],[1,1]]}])
        with self.assertRaisesRegex(ValueError, "polygon"):
            build_project(self.config)

    def test_create_config_validates_videos_and_refuses_overwrite(self):
        out = self.root / "new.json"
        project = create_config("Test", [{"id": "a", "path": str(self.root / "one.avi")},
                                         {"id": "b", "path": str(self.root / "two.avi"), "offset_seconds": 0.2}], out)
        self.assertEqual(project["timeline"]["start_seconds"], 0.2)
        self.assertEqual(len(json.loads(out.read_text())["cameras"]), 2)
        with self.assertRaises(FileExistsError):
            create_config("Test", [{"id": "a", "path": str(self.root / "one.avi")}], out)
        bad = self.root / "bad.json"
        with self.assertRaisesRegex(ValueError, "video"):
            create_config("Test", [{"id": "a", "path": str(self.root / "missing.mp4")}], bad)
        self.assertFalse(bad.exists())

    def test_analysis_roi_is_validated_against_video_dimensions(self):
        self.write([{"id":"a","path":"one.avi","analysis_roi":[10,5,40,30]}])
        camera=build_project(self.config)["cameras"][0]
        self.assertEqual(camera["analysis_roi"],[10,5,40,30])
        for roi in ([10,5,60,30], [1.5,0,10,10], [0,0,0,10]):
            self.write([{"id":"a","path":"one.avi","analysis_roi":roi}])
            with self.assertRaisesRegex(ValueError,"roi"): build_project(self.config)
