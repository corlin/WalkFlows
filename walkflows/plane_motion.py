"""Experimental frame-to-reference motion estimate; never updates a calibration."""
import cv2
import numpy as np


def estimate_motion(reference, current, polygon):
    ref = np.asarray(reference)
    cur = np.asarray(current)
    points = np.asarray(polygon, dtype=np.float64)
    if (ref.ndim not in (2, 3) or cur.shape != ref.shape or points.ndim != 2
            or points.shape[1] != 2 or len(points) < 3 or not np.isfinite(points).all()
            or abs(cv2.contourArea(points.astype(np.float32))) < 1):
        raise ValueError("invalid images or reference polygon")
    gray_ref = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY) if ref.ndim == 3 else ref
    gray_cur = cv2.cvtColor(cur, cv2.COLOR_BGR2GRAY) if cur.ndim == 3 else cur
    mask = np.zeros(ref.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [np.rint(points).astype(np.int32)], 255)
    detector = cv2.ORB_create(nfeatures=5000)
    a, da = detector.detectAndCompute(gray_ref, mask)
    b, db = detector.detectAndCompute(gray_cur, None)
    result = {"status": "insufficient_features", "current_to_reference": None,
              "reference_features": len(a), "current_features": len(b),
              "matches": 0, "inliers": 0}
    if da is None or db is None or len(a) < 4 or len(b) < 4:
        return result
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(db, da, k=2)
    good = [x for pair in pairs if len(pair) == 2 for x, y in [pair] if x.distance < .75*y.distance]
    result["matches"] = len(good)
    if len(good) < 8:
        return result
    source = np.float32([b[m.queryIdx].pt for m in good])
    target = np.float32([a[m.trainIdx].pt for m in good])
    matrix, inlier_mask = cv2.findHomography(source, target, cv2.RANSAC, 3.0)
    if matrix is None or inlier_mask is None or not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix) < 3:
        result["status"] = "estimation_failed"
        return result
    selected = inlier_mask.ravel().astype(bool)
    count = int(selected.sum())
    result["inliers"] = count
    result["inlier_ratio"] = float(count / len(good))
    if count < 8:
        result["status"] = "insufficient_inliers"
        return result
    if abs(matrix[2, 2]) < 1e-12:
        result["status"] = "estimation_failed"
        return result
    mapped = cv2.perspectiveTransform(source[selected, None, :], matrix)[:, 0, :]
    errors = np.linalg.norm(mapped - target[selected], axis=1)
    hull = cv2.convexHull(target[selected])
    result.update(status="estimated", current_to_reference=(matrix / matrix[2,2]).tolist(),
                  inlier_rmse_pixels=float(np.sqrt(np.mean(errors ** 2))),
                  reference_inlier_hull_area_pixels=float(cv2.contourArea(hull)),
                  scope="Exploratory frame registration only; validate ground points and camera motion independently.")
    return result
