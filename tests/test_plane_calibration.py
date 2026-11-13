import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import numpy as np
from walkflows.plane_calibration import fit_homography, apply_calibration, evaluate_check_points


class CalibrationTest(unittest.TestCase):
    def test_independent_check_reports_errors_and_outside_polygon(self):
        matrix=[[.02,0,2],[0,.02,3],[0,0,1]]
        result=evaluate_check_points(matrix, [[25,50],[150,50]], [[2.5,4],[5.2,4]],
                                     [[0,0],[100,0],[100,100],[0,100]])
        self.assertAlmostEqual(result["rmse"], (0.04/2)**.5)
        self.assertAlmostEqual(result["max_error"], .2)
        self.assertEqual([x["inside_calibration_polygon"] for x in result["checks"]],[True,False])
        self.assertAlmostEqual(result["checks"][1]["error"],.2)

    def test_independent_check_rejects_invalid_and_horizon_points(self):
        for image,plane in [([],[]),([[1,2]],[[1,float("nan")]]),([[0,0]],[[1,1]])]:
            with self.assertRaises(ValueError):
                evaluate_check_points([[1,0,0],[0,1,0],[1,0,0]], image, plane, None)
        with self.assertRaises(ValueError):
            evaluate_check_points([[1,0,0],[0,1,0],[0,0,0]], [[1,1]], [[1,1]], None)

    def test_check_command_detects_reused_fitting_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "project.json"
            config.write_text(json.dumps({"cameras":[{"id":"front","path":"video.mp4"}]}))
            points = root / "points.json"
            points.write_text(json.dumps({"image_points":[[0,0],[10,0],[10,10],[0,10]],
                                          "plane_points":[[0,0],[1,0],[1,1],[0,1]]}))
            mapped = root / "mapped.json"
            apply_calibration(config,"front",points,mapped)
            command=[sys.executable,"-m","walkflows","project-check-calibration","--config",str(mapped),
                     "--camera","front","--points",str(points)]
            result=subprocess.run(command,check=True,capture_output=True,text=True)
            report=json.loads(result.stdout)
            self.assertTrue(report["same_file_as_fit"])
            self.assertEqual(report["points"],4)
            self.assertLess(report["max_error"],1e-5)
            command[command.index("front")]="missing"
            self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)

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
