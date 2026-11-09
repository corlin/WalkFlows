"""Explicit output isolation and camera sets for the site03 007 experiments."""

CAMERAS = ("C0001020_v1", "C0001025_v1", "C0001029_v2",
           "C0001053_v5", "C0001055_v4", "C0001056_v2")


def resolve_mode(all_cameras):
    if not isinstance(all_cameras, bool):
        raise ValueError("mode must be boolean")
    return (CAMERAS, "site03-007-six-comparison") if all_cameras else (
        CAMERAS[-2:], "site03-007-comparison")
