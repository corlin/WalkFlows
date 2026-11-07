"""Run an offline, per-camera YOLO + ByteTrack baseline on local videos."""

import argparse
import csv
import hashlib
import json
import time
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO

from scripts.inspect_citic import plane_homography, transform
from walkflows.tracking import observation


def run_camera(model, camera, data_dir, output_dir, seconds, device):
    path = data_dir / f"{camera}.mp4"
    config = json.loads((data_dir / f"Node{camera}.json").read_text())
    homography = plane_homography(config)
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open {path}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if fps <= 0 or (width, height) != (config["image"]["width"], config["image"]["height"]):
        raise ValueError(f"Invalid fps or calibration dimensions for {camera}")
    video_path = output_dir / f"{camera}_tracked.mp4"
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        capture.release()
        raise RuntimeError(f"Cannot write {video_path}")
    # Independent camera tracker state: the caller creates a new model per camera.
    rows = []
    frames = 0
    start = time.perf_counter()
    try:
        while frames < round(seconds * fps):
            ok, frame = capture.read()
            if not ok:
                break
            result = model.track(frame, persist=True, tracker="bytetrack.yaml", classes=[0],
                                 conf=0.25, device=device, verbose=False)[0]
            if result.boxes is not None and result.boxes.id is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                ids = result.boxes.id.cpu().numpy()
                confidences = result.boxes.conf.cpu().numpy()
                for box, local_id, confidence in zip(boxes, ids, confidences):
                    row = observation(camera, frames, fps, local_id, confidence, box)
                    x, y = transform(homography, [[row["foot_x"], row["foot_y"]]])[0]
                    row.update(world_x=float(x), world_y=float(y))
                    rows.append(row)
            writer.write(result.plot())
            frames += 1
    finally:
        capture.release()
        writer.release()
    columns = ["camera", "frame", "timestamp_s", "local_id", "confidence", "left", "top",
               "right", "bottom", "foot_x", "foot_y", "world_x", "world_y"]
    with (output_dir / f"{camera}_observations.csv").open("w", newline="") as file:
        output = csv.DictWriter(file, fieldnames=columns)
        output.writeheader()
        output.writerows(rows)
    return {"camera": camera, "fps": fps, "frames": frames, "observations": len(rows),
            "local_track_ids": len({row['local_id'] for row in rows}),
            "elapsed_s": round(time.perf_counter() - start, 2)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/raw/citic"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/baseline"))
    parser.add_argument("--weights", type=Path, default=Path("data/models/yolo11n.pt"))
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument("--device", choices=("cpu", "mps"), default="cpu")
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    if not args.weights.is_file():
        parser.error(f"weights not found: {args.weights}")
    if args.device == "mps" and not torch.backends.mps.is_available():
        parser.error("MPS is unavailable")
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = {"weights": str(args.weights), "weights_sha256": hashlib.sha256(args.weights.read_bytes()).hexdigest(),
                "device": args.device, "seconds_requested": args.seconds, "tracker": "bytetrack.yaml",
                "note": "Local camera IDs only; world positions and timestamps are unvalidated estimates.",
                "runs": []}
    for camera in ("HallSeg", "HallWide"):
        metadata["runs"].append(run_camera(YOLO(str(args.weights)), camera, args.data, args.output,
                                           args.seconds, args.device))
        print(json.dumps(metadata["runs"][-1]), flush=True)
    (args.output / "run.json").write_text(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
