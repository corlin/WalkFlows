"""Approximate the published site03 sensor0 ground model with homographies.

This is a sample-specific calibration conversion, not ground truth or a generic
calibration solver. Input videos must be the unmodified binocular frames.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial.transform import Rotation

from walkflows.multicamera_processing import file_sha256


def derive(sensor, transform, bounds):
    rotation = Rotation.from_quat(transform["rotation"])
    position = np.asarray(transform["translation"], dtype=float)
    sensor_scale = np.asarray(sensor["format"], dtype=float) / [896, 672]
    hull = np.asarray(sensor["calib-hull"], np.float32)
    exponents = np.array([(d-j, j) for d in range(8, -1, -1) for j in range(d+1)])
    pixels, world_points, train = [], [], []
    for yi, y in enumerate(np.linspace(0, 671, 45)):
        for xi, x in enumerate(np.linspace(0, 895, 61)):
            pixel = np.array([x, y])
            calibrated_pixel = pixel * sensor_scale
            if cv2.pointPolygonTest(hull, tuple(calibrated_pixel), False) < 0:
                continue
            conditioned = (calibrated_pixel - np.asarray(sensor["center"])) * sensor["scale"]
            uv = np.asarray(sensor["A"]) @ (conditioned[0] ** exponents[:, 0] * conditioned[1] ** exponents[:, 1])
            ray = rotation.apply([*uv, 1.0])
            if abs(ray[2]) < 1e-8:
                continue
            distance = -position[2] / ray[2]
            world = position + distance * ray
            if (distance <= 0 or not np.isfinite(world).all() or
                    not (bounds[0] <= world[0] <= bounds[2] and bounds[1] <= world[1] <= bounds[3])):
                continue
            pixels.append(pixel)
            world_points.append(world[:2])
            train.append((xi + yi) % 3 != 0)
    pixels = np.asarray(pixels)
    world_points = np.asarray(world_points)
    train = np.asarray(train)
    if len(pixels) < 12 or train.sum() < 4 or (~train).sum() < 4:
        raise ValueError("insufficient valid calibration samples")
    matrix, _ = cv2.findHomography(pixels[train], world_points[train], 0)
    if matrix is None or not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix) < 3:
        raise ValueError("could not fit calibration")
    estimated = cv2.perspectiveTransform(pixels[~train].reshape(-1, 1, 2), matrix).reshape(-1, 2)
    error = np.linalg.norm(estimated - world_points[~train], axis=1)
    polygon = cv2.convexHull(pixels.astype(np.float32)).reshape(-1, 2)
    return matrix.tolist(), polygon.astype(float).tolist(), {
        "train_samples": int(train.sum()), "holdout_samples": int((~train).sum()),
        "median_scene_units": float(np.median(error)), "p95_scene_units": float(np.percentile(error, 95)),
        "max_scene_units": float(np.max(error))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--videos", required=True, type=Path)
    parser.add_argument("--calibration", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    scene_path = args.calibration / "site03_scene03.json"
    scene = json.loads(scene_path.read_text())
    if scene["global-transformation"] != {"translation": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": 1.0}:
        raise ValueError("unsupported scene transform")
    configs, reports = [], []
    for camera, transform in zip(scene["bcam-keys"], scene["bcam-transforms"]):
        if transform["scale"] != 1:
            raise ValueError("unsupported camera scale")
        sensor_path = args.calibration / (camera + ".json")
        video = (args.videos / (camera + ".mp4")).resolve(strict=True)
        capture = cv2.VideoCapture(str(video))
        ok, frame = capture.read()
        capture.release()
        if not ok or frame.shape[:2] != (672, 1792):
            raise ValueError("requires original 1792x672 binocular frames")
        sensor = json.loads(sensor_path.read_text())["sensor0"]
        matrix, polygon, stats = derive(sensor, transform, scene["hist-aabb"])
        configs.append({"id": camera, "path": str(video), "offset_seconds": 0,
                        "homography": matrix, "calibration_polygon": polygon,
                        "analysis_roi": [0, 0, 896, 672]})
        reports.append({"camera": camera, "sensor_sha256": file_sha256(sensor_path), **stats})
    args.output.mkdir(parents=True, exist_ok=False)
    config = {"name": "site03 sample, approximate left-image calibration", "cameras": configs}
    report = {"scope": "Approximation to supplied calibration model, not physical positioning accuracy. "
                       "Only sampled left image domain; input times set to zero, not verified synchronization.",
              "scene_sha256": file_sha256(scene_path), "script_sha256": file_sha256(__file__),
              "opencv": cv2.__version__, "cameras": reports}
    (args.output / "config.json").write_text(json.dumps(config, indent=2))
    (args.output / "calibration-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
