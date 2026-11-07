"""Common trajectory observation fields."""


def observation(camera, frame, fps, local_id, confidence, box):
    if fps <= 0:
        raise ValueError("fps must be positive")
    left, top, right, bottom = (float(value) for value in box)
    return {
        "camera": camera,
        "frame": frame,
        "timestamp_s": frame / fps,
        "local_id": int(local_id),
        "confidence": float(confidence),
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "foot_x": (left + right) / 2,
        "foot_y": bottom,
    }
