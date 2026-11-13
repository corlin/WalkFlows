import csv
import copy
import fcntl
import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from walkflows.multicamera_project import build_project
from walkflows.multicamera_processing import run_project, inspect_run


class Boxes:
    def __init__(self):
        class Array:
            def __init__(self, value): self.value = value
            def cpu(self): return self
            def tolist(self): return self.value
        self.xyxy = Array([[10, 10, 30, 40]])
        self.conf = Array([0.9])
        self.id = Array([1])


class FakeModel:
    def track(self, frame, **kwargs):
        return [type("Result", (), {"boxes": Boxes()})()]


class ProcessingTest(unittest.TestCase):
    def test_two_cameras_isolate_trackers_and_write_projected_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cameras = []
            for name in ("a", "b"):
                writer = cv2.VideoWriter(str(root / (name + ".avi")),
                                         cv2.VideoWriter_fourcc(*"MJPG"), 5, (64, 48))
                if not writer.isOpened():
                    self.skipTest("MJPG unavailable")
                for _ in range(3): writer.write(np.zeros((48, 64, 3), np.uint8))
                writer.release()
                cameras.append({"id": name, "path": name + ".avi", "offset_seconds": 0.2,
                                "homography": [[1, 0, 2], [0, 1, 3], [0, 0, 1]] if name == "b" else None, "calibration_polygon": [[0,0],[19,0],[19,47],[0,47]] if name == "b" else None})
            config = root / "config.json"
            config.write_text(json.dumps({"cameras": cameras}))
            model = root / "weights.pt"
            model.write_bytes(b"weights")
            instances = []
            def factory(path):
                instances.append(path)
                return FakeModel()
            output = root / "result"
            run_project(build_project(config), output, model, "cpu", model_factory=factory)
            self.assertEqual(len(instances), 2)
            state = json.loads((output / "run.json").read_text())
            self.assertEqual(state["status"], "completed")
            self.assertEqual([x["decoded_frames"] for x in state["cameras"]], [3, 3])
            with (output / "a.csv").open() as f: a = list(csv.DictReader(f))
            with (output / "b.csv").open() as f: b = list(csv.DictReader(f))
            self.assertEqual(len(a), 3)
            self.assertEqual(a[0]["world_x"], "")
            self.assertEqual(b[0]["world_x"], "")
            self.assertEqual(b[0]["world_y"], "")
            self.assertAlmostEqual(float(b[0]["timestamp_s"]), 0.2)
            with self.assertRaises(FileExistsError):
                run_project(build_project(config), output, model, "cpu", model_factory=factory)

    def test_failed_model_records_failure_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "a.avi"
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 5, (64, 48))
            if not writer.isOpened(): self.skipTest("MJPG unavailable")
            writer.write(np.zeros((48, 64, 3), np.uint8))
            writer.release()
            config = root / "config.json"
            config.write_text(json.dumps({"cameras": [{"id": "a", "path": "a.avi"}]}))
            weights = root / "weights.pt"
            weights.write_bytes(b"weights")
            class BrokenModel:
                def track(self, *args, **kwargs): raise RuntimeError("model failed")
            output = root / "result"
            with self.assertRaisesRegex(RuntimeError, "model failed"):
                run_project(build_project(config), output, weights, model_factory=lambda _: BrokenModel())
            state = json.loads((output / "run.json").read_text())
            self.assertEqual(state["status"], "failed")
            self.assertEqual(state["error"], "model failed")

    def test_resume_reuses_verified_camera_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("a", "b"):
                writer = cv2.VideoWriter(str(root / (name + ".avi")), cv2.VideoWriter_fourcc(*"MJPG"), 5, (64, 48))
                if not writer.isOpened(): self.skipTest("MJPG unavailable")
                for _ in range(2): writer.write(np.zeros((48, 64, 3), np.uint8))
                writer.release()
            config = root / "config.json"
            config.write_text(json.dumps({"cameras": [{"id":x,"path":x+".avi"} for x in ("a","b")]}))
            project=build_project(config)
            weights=root/"weights.pt"
            weights.write_bytes(b"weights")
            output=root/"run"
            count=[]
            class BrokenModel:
                def track(self,*args,**kwargs): raise RuntimeError("failure")
            def first_factory(_):
                count.append(1)
                return FakeModel() if len(count)==1 else BrokenModel()
            with self.assertRaisesRegex(RuntimeError,"failure"):
                run_project(project,output,weights,model_factory=first_factory)
            self.assertEqual(json.loads((output/"run.json").read_text())["status"],"failed")
            first_bytes=(output/"a.csv").read_bytes()
            count.clear()
            def resumed_factory(_):
                count.append(1)
                return FakeModel()
            changed=copy.deepcopy(project)
            changed["name"]="different"
            with self.assertRaisesRegex(ValueError,"changed"):
                run_project(changed,output,weights,model_factory=resumed_factory,resume=True)
            with (output/".run.lock").open("a+") as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaisesRegex(ValueError,"lock"):
                    run_project(project,output,weights,model_factory=resumed_factory,resume=True)
            (output/"b.csv").write_text("unowned")
            with self.assertRaises(FileExistsError):
                run_project(project,output,weights,model_factory=resumed_factory,resume=True)
            self.assertEqual((output/"b.csv").read_text(),"unowned")
            (output/"b.csv").unlink()
            count.clear()
            state=run_project(project,output,weights,model_factory=resumed_factory,resume=True)
            self.assertEqual(len(count),1)
            self.assertEqual((output/"a.csv").read_bytes(),first_bytes)
            self.assertEqual(state["status"],"completed")
            (output/"a.csv").write_text("changed")
            with self.assertRaisesRegex(ValueError,"hash"):
                run_project(project,output,weights,model_factory=resumed_factory,resume=True)

    def test_status_distinguishes_live_lock_and_abandoned_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"run.json").write_text(json.dumps({"status":"running","process_id":99999999,"cameras":[]}))
            (root/".run.lock").touch()
            self.assertEqual(inspect_run(root)["effective_status"],"interrupted_or_abandoned")
            with (root/".run.lock").open("a+") as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.assertEqual(inspect_run(root)["effective_status"],"running")
            (root/"run.json").write_text(json.dumps({"status":"running","cameras":[]}))
            self.assertEqual(inspect_run(root)["effective_status"],"unknown")

    def test_roi_inference_translates_boxes_to_original_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);video=root/"a.avi"
            writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*"MJPG"),5,(64,48))
            if not writer.isOpened(): self.skipTest("MJPG unavailable")
            writer.write(np.zeros((48,64,3),np.uint8));writer.release()
            config=root/"config.json"
            config.write_text(json.dumps({"cameras":[{"id":"a","path":"a.avi","analysis_roi":[10,0,54,48],
                                                        "homography":[[1,0,0],[0,1,0],[0,0,1]]}]}))
            weights=root/"w.pt";weights.write_bytes(b"weights")
            class CheckROI(FakeModel):
                def track(self,frame,**kwargs):
                    self.shape=frame.shape
                    return super().track(frame,**kwargs)
            model=CheckROI()
            out=root/"out"
            run_project(build_project(config),out,weights,model_factory=lambda _:model)
            self.assertEqual(model.shape[:2],(48,54))
            with (out/"a.csv").open() as f: row=next(csv.DictReader(f))
            self.assertEqual(float(row["left"]),20)
            self.assertEqual(float(row["world_x"]),30)
