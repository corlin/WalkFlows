"""Explicitly resolve one audited upstream reference boundary anomaly."""
import math


def normalize_reference_extent(scenario, reference, videos):
    if scenario != "004_site01_clutter":
        return reference, "declared_frame_count"
    frames = reference["frames"]
    points = [point for track in reference["tracks"] for point in track["path"]]
    if (frames != 499 or len(videos) != 2 or not points
            or any(type(point[2]) is not int or not 0 <= point[2] <= frames for point in points)
            or max(point[2] for point in points) != frames
            or any(video["frames"] != 500 or not math.isclose(video["fps"], 15, abs_tol=1e-5)
                   for video in videos)
            or not math.isclose(reference["frame-duration"] * 15, 1, abs_tol=1e-5)):
        raise ValueError("004 reference boundary lacks matching video evidence")
    return {**reference, "frames": frames + 1}, "verified_004_inclusive_boundary"
