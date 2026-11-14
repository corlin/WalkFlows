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

    def test_batch_applies_all_cameras_without_overwriting_or_partial_output(self):
        import cv2
        from walkflows.multicamera_processing import file_sha256
        from walkflows.plane_calibration import apply_calibration_bundle
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); cameras=[]; entries=[]
            for cid in ("a","b"):
                video=root/(cid+".avi")
                writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*"MJPG"),5,(64,48))
                if not writer.isOpened(): self.skipTest("MJPG unavailable")
                writer.write(np.zeros((48,64,3),np.uint8));writer.release()
                cameras.append({"id":cid,"path":str(video)})
                entries.append({"id":cid,"source_sha256":file_sha256(video),"width":64,"height":48,
                    "image_points":[[0,0],[60,0],[60,40],[0,40]],
                    "plane_points":[[0,0],[3,0],[3,2],[0,2]],
                    "coverage_polygon":[[5,5],[55,5],[55,15],[25,15],[25,35],[5,35]]})
            source=root/"project.json";source.write_text(json.dumps({"name":"test","cameras":cameras}))
            bundle=root/"points.json";bundle.write_text(json.dumps({"schema_version":1,"cameras":entries}))
            output=root/"mapped.json"
            result=apply_calibration_bundle(source,bundle,output)
            self.assertEqual(result["cameras"],2)
            mapped=json.loads(output.read_text())
            self.assertTrue(all(c.get("homography") for c in mapped["cameras"]))
            from walkflows.multicamera_processing import _project
            a=mapped["cameras"][0]
            self.assertNotEqual(_project(a["homography"],10,25,a["calibration_polygon"]),("",""))
            self.assertEqual(_project(a["homography"],40,25,a["calibration_polygon"]),("",""))
            self.assertFalse(any(c.get("homography") for c in json.loads(source.read_text())["cameras"]))
            with self.assertRaises(FileExistsError): apply_calibration_bundle(source,bundle,output)
            entries[1]["source_sha256"]="0"*64
            bundle.write_text(json.dumps({"schema_version":1,"cameras":entries}))
            with self.assertRaisesRegex(ValueError,"source"):
                apply_calibration_bundle(source,bundle,root/"bad.json")
            self.assertFalse((root/"bad.json").exists())
            entries.pop()
            bundle.write_text(json.dumps({"schema_version":1,"cameras":entries}))
            with self.assertRaisesRegex(ValueError,"camera"):
                apply_calibration_bundle(source,bundle,root/"missing.json")
            self.assertFalse((root/"missing.json").exists())

    def test_rejects_invalid_coverage_polygon(self):
        from walkflows.plane_calibration import validate_coverage_polygon
        hull=[[0,0],[60,0],[60,40],[0,40]]
        for polygon in ([[[5,5],[55,35],[55,5],[5,35]],
                         [[5,5],[61,5],[55,35],[5,35]],
                         [[5,5],[55,5],[55,5],[5,35]]]):
            with self.assertRaises(ValueError):
                validate_coverage_polygon(polygon,hull,64,48)

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
