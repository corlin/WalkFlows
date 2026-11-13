"""Validate a generic local multicamera project without running inference."""
import hashlib
import json
import math
import re
import tempfile
from pathlib import Path

import cv2
import numpy as np


def _video(path):
    capture = cv2.VideoCapture(str(path))
    try:
        ok, frame = capture.read()
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if not ok or frame is None or not math.isfinite(fps) or fps <= 0 or not math.isfinite(count) or count < 1:
            raise ValueError(f"unreadable video or invalid metadata: {path}")
        height, width = frame.shape[:2]
        frames = int(count)
        if width < 1 or height < 1 or frames < 1:
            raise ValueError(f"invalid video metadata: {path}")
    finally:
        capture.release()
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": str(path), "width": width, "height": height, "fps": fps,
            "frame_count": frames, "duration_seconds": frames / fps, "sha256": digest.hexdigest()}


def build_project(config_path, *, allow_no_overlap=False):
    config_path = Path(config_path).expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("cameras"), list) or not config["cameras"]:
        raise ValueError("project requires at least one camera")
    cameras, seen = [], set()
    for item in config["cameras"]:
        if not isinstance(item, dict):
            raise ValueError("invalid camera")
        camera_id = item.get("id")
        if not isinstance(camera_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", camera_id) or camera_id in seen:
            raise ValueError("invalid or duplicate camera id")
        seen.add(camera_id)
        raw_path = item.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("camera video path required")
        path = Path(raw_path).expanduser()
        path = (config_path.parent / path).resolve()
        if not path.is_file():
            raise ValueError(f"video not found: {path}")
        try:
            offset = float(item.get("offset_seconds", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid camera offset") from exc
        if not math.isfinite(offset):
            raise ValueError("invalid camera offset")
        homography = item.get("homography")
        if homography is not None:
            try:
                matrix = np.asarray(homography, dtype=float)
                if matrix.shape != (3, 3) or not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix) < 3:
                    raise ValueError("invalid homography")
                homography = matrix.tolist()
            except (TypeError, ValueError, np.linalg.LinAlgError) as exc:
                raise ValueError("invalid homography") from exc
        polygon = item.get("calibration_polygon")
        if polygon is not None:
            try:
                contour = np.asarray(polygon, dtype=np.float32)
                if (homography is None or contour.ndim != 2 or contour.shape[1] != 2
                        or len(contour) < 3 or not np.isfinite(contour).all()
                        or abs(cv2.contourArea(contour)) < 1e-6):
                    raise ValueError("invalid calibration polygon")
                polygon = contour.astype(float).tolist()
            except (TypeError, ValueError, cv2.error) as exc:
                raise ValueError("invalid calibration polygon") from exc
        video = _video(path)
        roi = item.get("analysis_roi")
        if roi is not None:
            if (not isinstance(roi, list) or len(roi) != 4 or
                    any(type(v) is not int for v in roi)):
                raise ValueError("invalid analysis roi")
            x, y, width, height = roi
            if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > video["width"] or y + height > video["height"]:
                raise ValueError("analysis roi outside video")
        cameras.append({"id": camera_id, "offset_seconds": offset, "homography": homography,
                        "calibration_polygon": polygon, "calibration_provenance": item.get("calibration_provenance"),
                        "analysis_roi": roi, "video": video})
    start = max(c["offset_seconds"] for c in cameras)
    end = min(c["offset_seconds"] + c["video"]["duration_seconds"] for c in cameras)
    if end <= start and not allow_no_overlap:
        raise ValueError("camera videos have no temporal overlap")
    return {"schema_version": 1, "name": config.get("name", config_path.stem),
            "source_config": str(config_path), "cameras": cameras,
            "timeline": {"start_seconds": start, "end_seconds": end},
            "status": "validated_inputs_only"}



def create_config(name, cameras, output_path):
    """Create a new validated config, never overwriting another project."""
    output_path = Path(output_path).expanduser().resolve()
    if output_path.exists():
        raise FileExistsError(str(output_path))
    if not isinstance(name, str) or not name.strip():
        raise ValueError("project name required")
    normalized = []
    for camera in cameras:
        if not isinstance(camera, dict) or not isinstance(camera.get("path"), str) or not camera["path"].strip():
            raise ValueError("camera video path required")
        item = dict(camera)
        item["path"] = str(Path(item["path"]).expanduser().resolve())
        normalized.append(item)
    config = {"name": name, "cameras": normalized}
    content = json.dumps(config, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    with tempfile.TemporaryDirectory(prefix=".walkflows-validate-", dir=output_path.parent) as tmp:
        candidate = Path(tmp) / "project.json"
        candidate.write_text(content, encoding="utf-8")
        result = build_project(candidate)
    with output_path.open("x", encoding="utf-8") as target:
        target.write(content)
    result["source_config"] = str(output_path)
    return result



def apply_offsets(config_path, offsets_path, output_path):
    """Apply user-supplied time offsets to a new validated project file."""
    config_path = Path(config_path).expanduser().resolve()
    offsets_path = Path(offsets_path).expanduser().resolve()
    output_path = Path(output_path).expanduser().resolve()
    if output_path.exists():
        raise FileExistsError(str(output_path))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    offsets = json.loads(offsets_path.read_text(encoding="utf-8")).get("offsets")
    cameras = config.get("cameras")
    if not isinstance(cameras, list) or not all(isinstance(c, dict) for c in cameras):
        raise ValueError("invalid cameras")
    if not isinstance(offsets, dict):
        raise ValueError("invalid offsets")
    ids = {c.get("id") for c in cameras}
    if set(offsets) - ids:
        raise ValueError("offset references unknown camera")
    for key, value in offsets.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("invalid camera offset")
    for camera in cameras:
        path = camera.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("camera video path required")
        camera["path"] = str((config_path.parent / Path(path).expanduser()).resolve())
        if camera.get("id") in offsets:
            camera["offset_seconds"] = offsets[camera["id"]]
    content = json.dumps(config, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    with tempfile.TemporaryDirectory(prefix=".walkflows-validate-", dir=output_path.parent) as tmp:
        candidate = Path(tmp) / "project.json"
        candidate.write_text(content, encoding="utf-8")
        result = build_project(candidate)
    with output_path.open("x", encoding="utf-8") as target:
        target.write(content)
    result["source_config"] = str(output_path)
    return result
