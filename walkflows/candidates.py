"""Report spatial candidate pairs; this does not assign global identities."""

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def candidates_at_frame(left, right, max_distance):
    pairs = []
    for a in left:
        for b in right:
            if a["frame"] != b["frame"]:
                continue
            distance = math.hypot(a["world_x"] - b["world_x"], a["world_y"] - b["world_y"])
            if math.isfinite(distance) and distance <= max_distance:
                pairs.append({"frame": a["frame"], "left_id": a["local_id"],
                              "right_id": b["local_id"], "distance": distance})
    return pairs


def read_tracks(path):
    grouped = defaultdict(list)
    with path.open(newline="") as file:
        for row in csv.DictReader(file):
            frame = int(row["frame"])
            grouped[frame].append({"frame": frame, "local_id": int(row["local_id"]),
                                   "world_x": float(row["world_x"]), "world_y": float(row["world_y"])})
    return grouped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/baseline"))
    parser.add_argument("--max-distance", type=float, default=1.0)
    args = parser.parse_args()
    if args.max_distance <= 0:
        parser.error("--max-distance must be positive")
    left = read_tracks(args.input / "HallSeg_observations.csv")
    right = read_tracks(args.input / "HallWide_observations.csv")
    groups = defaultdict(list)
    for frame in sorted(left.keys() & right.keys()):
        for p in candidates_at_frame(left[frame], right[frame], args.max_distance):
            groups[(p["left_id"], p["right_id"])].append(p)
    report = [{"hallseg_id": a, "hallwide_id": b, "overlap_frames": len(rows),
               "first_frame": rows[0]["frame"], "last_frame": rows[-1]["frame"],
               "median_distance": round(statistics.median(r["distance"] for r in rows), 3)}
              for (a, b), rows in sorted(groups.items())]
    result = {"assumptions": "same frame index; projected positions; no synchronization or identity validation",
              "max_distance": args.max_distance, "candidates": report}
    (args.input / "candidate_pairs.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
