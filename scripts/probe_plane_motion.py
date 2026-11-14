"""Compare video frames to an anchor using a user-supplied reference polygon."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2

from walkflows.plane_motion import estimate_motion
from walkflows.multicamera_processing import file_sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--polygon", required=True, type=Path, help="JSON array of reference-frame ground pixels")
    parser.add_argument("--frames", required=True, type=int, nargs="+")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if any(frame < 0 for frame in args.frames):
        parser.error("frame numbers must be non-negative")
    polygon_bytes = args.polygon.read_bytes()
    polygon = json.loads(polygon_bytes)
    cap = cv2.VideoCapture(str(args.video))
    try:
        ok, reference = cap.read()
        if not ok:
            raise ValueError("cannot decode reference frame")
        results = []
        for index in args.frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, current = cap.read()
            if not ok:
                results.append({"frame": index, "status": "decode_failed"})
            else:
                results.append({"frame": index, **estimate_motion(reference, current, polygon)})
        report = {"video": str(args.video.resolve()), "video_sha256": file_sha256(args.video), "polygon_sha256": hashlib.sha256(polygon_bytes).hexdigest(),
                  "reference_frame": 0, "fps": cap.get(cv2.CAP_PROP_FPS), "results": results,
                  "scope": "Experimental feature registration; not verified floor calibration or absolute accuracy."}
        with args.output.open("x", encoding="utf-8") as f:
            json.dump(report, f, indent=2, allow_nan=False)
            f.write("\n")
        print(json.dumps(report, indent=2, allow_nan=False))
    finally:
        cap.release()


if __name__ == "__main__":
    main()
