import unittest
import json
import tempfile
from pathlib import Path
import numpy as np
from walkflows.plane_calibration import fit_homography, apply_calibration


class CalibrationTest(unittest.TestCase):
    def test_fits_known_mapping_and_reports_error(self):
        image = [[0, 0], [100, 0], [100, 100], [0, 100], [50, 40]]
        world = [[2, 3], [4, 3], [4, 5], [2, 5], [3, 3.8]]
        result = fit_homography(image, world)
        self.assertLess(result["rmse"], 1e-5)
        h = np.array(result["homography"])
        point = h @ [25, 50, 1]
        np.testing.assert_allclose(point[:2] / point[2], [2.5, 4], atol=1e-5)

    def test_rejects_collinear_and_nonfinite_points(self):
        with self.assertRaises(ValueError):
            fit_homography([[0,0],[1,1],[2,2],[3,3]], [[0,0],[1,1],[2,2],[3,3]])
        with self.assertRaises(ValueError):
            fit_homography([[0,0],[1,0],[1,1],[0,float("nan")]], [[0,0],[1,0],[1,1],[0,1]])

    def test_apply_creates_new_config_without_changing_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "project.json"
            original = {"name":"room","cameras":[{"id":"cam1","path":"video.mp4"},{"id":"cam2","path":"other.mp4"}]}
            config.write_text(json.dumps(original))
            points = root / "points.json"
            points.write_text(json.dumps({"image_points":[[0,0],[10,0],[10,10],[0,10]],
                                          "plane_points":[[0,0],[1,0],[1,1],[0,1]]}))
            target = root / "export" / "mapped.json"
            target.parent.mkdir()
            apply_calibration(config, "cam1", points, target)
            out = json.loads(target.read_text())
            self.assertEqual(json.loads(config.read_text()),original)
            self.assertEqual(out["cameras"][0]["path"],str(root / "video.mp4"))
            self.assertIn("homography",out["cameras"][0])
            self.assertNotIn("homography",out["cameras"][1])
            with self.assertRaises(FileExistsError): apply_calibration(config,"cam1",points,target)
            with self.assertRaisesRegex(ValueError,"camera"): apply_calibration(config,"missing",points,root/"other.json")
