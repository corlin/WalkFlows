"""Conditional comparison of per-camera positions to frame-indexed reference points."""
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from walkflows.multicamera_processing import file_sha256
from walkflows.reference_eval import convert_reference, match_positions


def evaluate_run(directory, reference_path, threshold):
    directory = Path(directory).resolve(strict=True)
    reference_path = Path(reference_path).resolve(strict=True)
    if not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold must be positive")
    run_path = directory / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    if run.get("status") != "completed":
        raise ValueError("run must be complete")
    reference_data = json.loads(reference_path.read_text(encoding="utf-8"))["track_results"]
    if reference_data.get("start-frame") != 0:
        raise ValueError("only zero start-frame alignment is supported")
    reference = convert_reference(reference_data)
    cameras = run["project"]["cameras"]
    results = {x["id"]: x for x in run["cameras"]}
    if len(results) != len(cameras):
        raise ValueError("camera results incomplete")
    output = []
    for camera in cameras:
        cid = camera["id"]
        result = results.get(cid)
        if not result or result.get("status") != "completed":
            raise ValueError("camera result incomplete: " + cid)
        if camera["offset_seconds"] != 0 or not math.isclose(
                1 / camera["video"]["fps"], reference["frame_duration"], rel_tol=1e-5, abs_tol=1e-7):
            raise ValueError("reference alignment requires zero offsets and matching frame duration")
        if file_sha256(camera["video"]["path"]) != camera["video"]["sha256"]:
            raise ValueError("video hash mismatch: " + cid)
        csv_path = directory / (cid + ".csv")
        if file_sha256(csv_path) != result["observations_sha256"]:
            raise ValueError("observation hash mismatch: " + cid)
        frames = defaultdict(list)
        total=0; valid=0; untracked=0; outside=0; duplicate=0
        with csv_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                total += 1
                frame=int(row["frame"])
                if not (0 <= frame < reference_data["frames"]):
                    outside += 1
                    continue
                if not row["world_x"] or not row["world_y"]:
                    continue
                x,y=float(row["world_x"]),float(row["world_y"])
                if not math.isfinite(x) or not math.isfinite(y):
                    continue
                valid += 1
                if not row["local_id"]:
                    untracked += 1
                    continue
                frames[frame].append({"id":int(row["local_id"]),"x":x,"y":y})
        matched=[];refs=Counter(); eligible=0; compared_frames=0
        for frame, points in frames.items():
            counts=Counter(p["id"] for p in points)
            duplicate += sum(counts[p["id"]] > 1 for p in points)
            clean=[p for p in points if counts[p["id"]] == 1]
            if reference["by_frame"][frame]:
                compared_frames += 1
                eligible += len(clean)
            for match in match_positions(clean,reference["by_frame"][frame],threshold):
                matched.append(match["distance"]);refs[str(match["reference_id"])] += 1
        output.append({"camera":cid,"decoded_frames":result["decoded_frames"],"observations":total,
                       "projected_observations":valid,"outside_reference_frames":outside,
                       "projected_without_local_id":untracked,"duplicate_id_rows_excluded":duplicate,
                       "frames_with_projected_tracks_and_reference":compared_frames,
                       "projected_track_observations_with_reference":eligible,
                       "matched_observations":len(matched),
                       "median_matched_distance":float(np.median(matched)) if matched else None,
                       "p95_matched_distance":float(np.percentile(matched,95)) if matched else None,
                       "reference_id_match_counts":dict(refs)})
    return {"scope":"Conditional one-to-one proximity to supplied reference, not verified identity, recall, "
                    "physical accuracy or customer counts; matches are truncated by threshold.",
            "alignment_assumption":"Reference and source share frame zero, constant frame duration and scene coordinates; "
                                   "metadata checks do not prove actual synchronization.",
            "threshold_scene_units":float(threshold),"reference_frames":reference_data["frames"],
            "reference_tracks":reference["track_count"],"reference_sha256":file_sha256(reference_path),
            "run_sha256":file_sha256(run_path),"implementation_sha256":file_sha256(__file__),
            "cameras":output}
