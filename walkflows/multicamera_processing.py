"""Generic sequential video inference; no cross-camera identity claims."""
import csv
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import time
import tempfile
from pathlib import Path

import cv2
import numpy as np


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _state(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(tmp, path)


def _project(matrix, x, y, polygon=None):
    if matrix is None:
        return "", ""
    if polygon is not None and cv2.pointPolygonTest(np.asarray(polygon, dtype=np.float32), (x, y), False) < 0:
        return "", ""
    mapped = np.asarray(matrix) @ np.array([x, y, 1.0])
    if not np.isfinite(mapped).all() or abs(mapped[2]) < 1e-9:
        return "", ""
    result = mapped[:2] / mapped[2]
    return tuple(map(float, result)) if np.isfinite(result).all() else ("", "")


def _version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def inspect_run(output):
    """Report journal status and whether a currently held lock confirms activity."""
    output = Path(output).expanduser().resolve()
    state = json.loads((output / "run.json").read_text(encoding="utf-8"))
    effective = state.get("status", "unknown")
    busy = None
    try:
        with (output / ".run.lock").open("r") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                busy = True
            else:
                busy = False
                fcntl.flock(lock, fcntl.LOCK_UN)
    except OSError:
        pass
    if effective == "running":
        if busy:
            effective = "running"
        elif busy is False and type(state.get("process_id")) is int and state["process_id"] > 0:
            try:
                os.kill(state["process_id"], 0)
            except ProcessLookupError:
                effective = "interrupted_or_abandoned"
            except PermissionError:
                effective = "unknown"
            else:
                effective = "unknown"
        else:
            effective = "unknown"
    return {"effective_status": effective, "lock_busy": busy, "journal": state}


def run_project(project, output, weights, device="cpu", *, model_factory=None, resume=False):
    output, weights = Path(output).expanduser().resolve(), Path(weights).expanduser().resolve()
    if not weights.is_file():
        raise ValueError("model weights do not exist")
    if resume:
        if not output.is_dir():
            raise ValueError("resume output does not exist")
    else:
        output.mkdir(parents=True, exist_ok=False)
    with (output / ".run.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("another process holds the run lock") from exc
        try:
            return _run_locked(project, output, weights, device, model_factory, resume)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _run_locked(project, output, weights, device, model_factory, resume):
    weights_hash = file_sha256(weights)
    state_path = output / "run.json"
    model_info = {"path": str(weights), "sha256": weights_hash, "device": str(device),
                  "tracker": "bytetrack.yaml", "confidence": 0.25}
    versions = {name: _version(name) for name in ("ultralytics", "torch", "opencv-python", "numpy")}
    spec = importlib.util.find_spec("ultralytics")
    tracker = Path(spec.origin).parent / "cfg/trackers/bytetrack.yaml" if spec and spec.origin else None
    implementation = {"processor_sha256": file_sha256(__file__),
                      "project_sha256": file_sha256(Path(__file__).with_name("multicamera_project.py")),
                      "tracker_sha256": file_sha256(tracker) if tracker and tracker.is_file() else None}
    if resume:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if (state.get("project") != project or state.get("model") != model_info or
                state.get("versions") != versions or state.get("implementation") != implementation):
            raise ValueError("project, model, parameters or environment changed; cannot resume")
        if state.get("status") not in ("failed", "running", "completed"):
            raise ValueError("invalid run status")
        if state.get("status") == "running":
            pid = state.get("process_id")
            if type(pid) is not int or pid <= 0:
                raise ValueError("cannot verify whether the prior process is still active")
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                pass
            except PermissionError as exc:
                raise ValueError("cannot verify whether the prior process is still active") from exc
            else:
                raise ValueError("prior process may still be active")
        ids = [entry.get("id") for entry in state.get("cameras", [])]
        expected = [camera["id"] for camera in project["cameras"]]
        if len(ids) != len(set(ids)) or any(cid not in expected for cid in ids):
            raise ValueError("invalid camera state")
        for camera in project["cameras"]:
            if file_sha256(camera["video"]["path"]) != camera["video"]["sha256"]:
                raise ValueError("video hash changed: " + camera["id"])
        for entry in state["cameras"]:
            if entry.get("status") == "completed":
                path = output / (entry["id"] + ".csv")
                if not path.is_file() or file_sha256(path) != entry.get("observations_sha256"):
                    raise ValueError("observation hash changed: " + entry["id"])
        if state["status"] == "completed":
            if len(state["cameras"]) != len(project["cameras"]) or any(e.get("status") != "completed" for e in state["cameras"]):
                raise ValueError("incomplete completed run")
            return state
        state.pop("error", None)
        state.pop("finished_unix_s", None)
        state["resumed_unix_s"] = time.time()
        state["status"] = "running"
        state["process_id"] = os.getpid()
    else:
        state = {"status": "running", "started_unix_s": time.time(), "project": project,
                 "process_id": os.getpid(), "model": model_info,
                 "scope": "Per-camera observations only; local IDs are not cross-camera identities. "
                          "Projected box bottoms are unvalidated estimates.",
                 "versions": versions, "implementation": implementation, "cameras": []}
    _state(state_path, state)
    fields = ["frame", "timestamp_s", "local_id", "confidence", "left", "top", "right",
              "bottom", "foot_x", "foot_y", "world_x", "world_y"]
    try:
        if model_factory is None:
            from ultralytics import YOLO
            model_factory = YOLO
        for camera in project["cameras"]:
            source = camera["video"]
            if file_sha256(source["path"]) != source["sha256"]:
                raise ValueError("video changed since validation: " + camera["id"])
            existing = next((e for e in state["cameras"] if e["id"] == camera["id"]), None)
            if existing and existing.get("status") == "completed":
                continue
            entry = {"id": camera["id"], "status": "running", "decoded_frames": 0, "observations": 0}
            if existing is None:
                state["cameras"].append(entry)
            else:
                state["cameras"][state["cameras"].index(existing)] = entry
            _state(state_path, state)
            model = model_factory(str(weights))
            cap = cv2.VideoCapture(source["path"])
            if not cap.isOpened():
                raise ValueError("cannot open video: " + camera["id"])
            csv_path = output / (camera["id"] + ".csv")
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", newline="", encoding="utf-8", dir=output,
                                                 prefix="." + camera["id"] + ".", suffix=".part",
                                                 delete=False) as handle:
                    temporary = Path(handle.name)
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    while True:
                        ok, frame = cap.read()
                        if not ok:
                            break
                        if frame.shape[:2] != (source["height"], source["width"]):
                            raise ValueError("video dimensions changed: " + camera["id"])
                        index = entry["decoded_frames"]
                        roi = camera.get("analysis_roi")
                        x0, y0, width, height = roi if roi is not None else (0, 0, source["width"], source["height"])
                        image = frame[y0:y0 + height, x0:x0 + width]
                        result = model.track(image, persist=True, tracker="bytetrack.yaml", classes=[0],
                                             conf=0.25, device=device, verbose=False)[0]
                        boxes = result.boxes
                        if boxes is not None:
                            coords = boxes.xyxy.cpu().tolist()
                            scores = boxes.conf.cpu().tolist()
                            ids = boxes.id.cpu().tolist() if boxes.id is not None else [None] * len(coords)
                            if len(coords) != len(scores) or len(coords) != len(ids):
                                raise ValueError("inconsistent detection output")
                            for box, score, local_id in zip(coords, scores, ids):
                                if len(box) != 4 or not all(math.isfinite(float(v)) for v in [*box, score]):
                                    continue
                                left, top, right, bottom = map(float, box)
                                left, right = left + x0, right + x0
                                top, bottom = top + y0, bottom + y0
                                foot_x, foot_y = (left + right) / 2, bottom
                                wx, wy = _project(camera["homography"], foot_x, foot_y, camera.get("calibration_polygon"))
                                writer.writerow({"frame": index, "timestamp_s": camera["offset_seconds"] + index / source["fps"],
                                                 "local_id": int(local_id) if local_id is not None else "",
                                                 "confidence": float(score), "left": left, "top": top,
                                                 "right": right, "bottom": bottom, "foot_x": foot_x, "foot_y": foot_y,
                                                 "world_x": wx, "world_y": wy})
                                entry["observations"] += 1
                        entry["decoded_frames"] += 1
                        if entry["decoded_frames"] % 100 == 0:
                            handle.flush()
                            _state(state_path, state)
                if entry["decoded_frames"] == 0:
                    raise ValueError("no frames decoded: " + camera["id"])
                if file_sha256(source["path"]) != source["sha256"]:
                    raise ValueError("video changed during processing: " + camera["id"])
                # An unverified file must never be replaced, including after a crash.
                os.link(temporary, csv_path)
                temporary.unlink()
                temporary = None
            finally:
                cap.release()
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            entry["status"] = "completed"
            entry["metadata_frame_count"] = source["frame_count"]
            entry["frame_count_matches_metadata"] = entry["decoded_frames"] == source["frame_count"]
            entry["observations_sha256"] = file_sha256(csv_path)
            _state(state_path, state)
        if file_sha256(weights) != weights_hash:
            raise ValueError("model weights changed during processing")
        state["status"] = "completed"
        state["finished_unix_s"] = time.time()
        _state(state_path, state)
        return state
    except Exception as exc:
        state["status"] = "failed"
        state["error"] = str(exc)
        state["finished_unix_s"] = time.time()
        _state(state_path, state)
        raise
