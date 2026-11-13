"""Fit an image-to-plane map from user-supplied matching points."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


def fit_homography(image_points, plane_points):
    try:
        image = np.asarray(image_points, dtype=np.float64)
        plane = np.asarray(plane_points, dtype=np.float64)
        if (image.ndim != 2 or image.shape[1] != 2 or plane.shape != image.shape
                or len(image) < 4 or not np.isfinite(image).all() or not np.isfinite(plane).all()):
            raise ValueError("at least four finite paired 2D points required")
        if np.linalg.matrix_rank(image - image.mean(axis=0)) < 2 or np.linalg.matrix_rank(plane - plane.mean(axis=0)) < 2:
            raise ValueError("points must not be collinear")
        matrix, _ = cv2.findHomography(image, plane, 0)
        if matrix is None or not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix) < 3:
            raise ValueError("degenerate point configuration")
        projected = cv2.perspectiveTransform(image.reshape(-1, 1, 2), matrix).reshape(-1, 2)
        if not np.isfinite(projected).all():
            raise ValueError("non-finite mapping")
        errors = np.linalg.norm(projected - plane, axis=1)
        return {"homography": matrix.tolist(),
                "calibration_polygon": cv2.convexHull(image.astype(np.float32)).reshape(-1, 2).astype(float).tolist(),
                "points": len(image), "rmse": float(np.sqrt(np.mean(errors ** 2))),
                "max_error": float(errors.max()),
                "scope": "Training-point residual in supplied plane units; not independent accuracy."}
    except (TypeError, ValueError, cv2.error, np.linalg.LinAlgError) as exc:
        raise ValueError("invalid calibration: " + str(exc)) from exc



def apply_calibration(config_path, camera_id, points_path, output_path):
    """Create a new config; resolve all source paths relative to the old config."""
    config_path = Path(config_path).expanduser().resolve()
    points_path = Path(points_path).expanduser().resolve()
    output_path = Path(output_path).expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    points_bytes = points_path.read_bytes()
    points = json.loads(points_bytes)
    result = fit_homography(points["image_points"], points["plane_points"])
    cameras = config.get("cameras")
    if not isinstance(cameras, list) or not all(isinstance(c, dict) for c in cameras):
        raise ValueError("invalid camera configuration")
    matches = [c for c in cameras if c.get("id") == camera_id]
    if len(matches) != 1:
        raise ValueError("camera must match exactly one entry")
    for camera in cameras:
        if not isinstance(camera.get("path"), str) or not camera["path"]:
            raise ValueError("invalid camera path")
        camera["path"] = str((config_path.parent / Path(camera["path"]).expanduser()).resolve())
    matches[0]["homography"] = result["homography"]
    matches[0]["calibration_polygon"] = result["calibration_polygon"]
    matches[0]["calibration_provenance"] = {
        "points_sha256": hashlib.sha256(points_bytes).hexdigest(),
        "points": result["points"], "rmse": result["rmse"], "max_error": result["max_error"],
        "scope": result["scope"]}
    content = json.dumps(config, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    with output_path.open("x", encoding="utf-8") as output:
        output.write(content)
    return result
