"""Inspect the local CITIC camera files and calibration geometry."""

import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/raw/citic"
OUTPUT = ROOT / "data/processed/citic_inspection"


def plane_homography(config):
    calibration = config["calibration"]
    if "homography" in calibration:
        return np.asarray(calibration["homography"], dtype=np.float64)
    intrinsics = np.asarray(calibration["intr_mtx"], dtype=np.float64)
    extrinsics = np.asarray(calibration["R_t_mat"], dtype=np.float64)
    # For z=0, K [r1 r2 t] projects the common ground plane to image.
    world_to_image = intrinsics @ extrinsics[:, [0, 1, 3]]
    return np.linalg.inv(world_to_image)


def transform(matrix, points):
    return cv2.perspectiveTransform(np.asarray(points, np.float64).reshape(-1, 1, 2), matrix).reshape(-1, 2)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    for camera in ("HallSeg", "HallWide"):
        config = json.loads((DATA / f"Node{camera}.json").read_text())
        cap = cv2.VideoCapture(str(DATA / f"{camera}.mp4"))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open {camera} video")
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if (width, height) != (config["image"]["width"], config["image"]["height"]):
            raise ValueError(f"{camera} dimensions differ from calibration")
        decoded = []
        for sec in (0, 5, 10, 20, 30):
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(sec * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot decode {camera} at {sec}s")
            if not cv2.imwrite(str(OUTPUT / f"{camera}_{sec:02}.jpg"), frame):
                raise RuntimeError(f"Cannot write frame for {camera} at {sec}s")
            decoded.append(sec)
        cap.release()
        h = plane_homography(config)
        sample = np.array([[width * .5, height * .7], [width * .35, height * .8], [width * .65, height * .8]])
        ground = transform(h, sample)
        back = transform(np.linalg.inv(h), ground)
        summary[camera] = {
            "width": width, "height": height, "fps": fps, "frames": frame_count,
            "decoded_seconds": decoded, "image_points": sample.tolist(),
            "projected_ground_points": ground.round(4).tolist(),
            "roundtrip_max_error_px": float(np.max(np.linalg.norm(back - sample, axis=1))),
        }
    (OUTPUT / "inspection.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("Round-trip checks algebra only; they do not establish calibration accuracy or synchronization.")


if __name__ == "__main__":
    main()
