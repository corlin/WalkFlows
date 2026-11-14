"""Fit an image-to-plane map from user-supplied matching points."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


def fit_homography(image_points, plane_points):
    try:
        image = np.asarray(image_points, dtype=np.float64)
        plane = np.asarray(plane_points, dtype=np.float64)
        if (image.ndim != 2 or image.shape[1] != 2 or plane.shape != image.shape
                or len(image) < 4 or not np.isfinite(image).all() or not np.isfinite(plane).all()):
            raise ValueError("at least four finite paired 2D points required")
        if np.linalg.matrix_rank(image - image.mean(axis=0)) < 2 or np.linalg.matrix_rank(plane - plane.mean(axis=0)) < 2:
            raise ValueError("points must not be collinear")
        matrix, _ = cv2.findHomography(image, plane, 0)
        if matrix is None or not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix) < 3:
            raise ValueError("degenerate point configuration")
        projected = cv2.perspectiveTransform(image.reshape(-1, 1, 2), matrix).reshape(-1, 2)
        if not np.isfinite(projected).all():
            raise ValueError("non-finite mapping")
        errors = np.linalg.norm(projected - plane, axis=1)
        return {"homography": matrix.tolist(),
                "calibration_polygon": cv2.convexHull(image.astype(np.float32)).reshape(-1, 2).astype(float).tolist(),
                "points": len(image), "rmse": float(np.sqrt(np.mean(errors ** 2))),
                "max_error": float(errors.max()),
                "scope": "Training-point residual in supplied plane units; not independent accuracy."}
    except (TypeError, ValueError, cv2.error, np.linalg.LinAlgError) as exc:
        raise ValueError("invalid calibration: " + str(exc)) from exc



def evaluate_check_points(homography, image_points, plane_points, polygon=None):
    # Evaluate supplied check pairs; the user must establish independence.
    try:
        matrix = np.asarray(homography, dtype=np.float64)
        image = np.asarray(image_points, dtype=np.float64)
        plane = np.asarray(plane_points, dtype=np.float64)
        if (matrix.shape != (3, 3) or not np.isfinite(matrix).all()
                or np.linalg.matrix_rank(matrix) < 3 or image.ndim != 2
                or image.shape[1] != 2 or len(image) < 1 or image.shape != plane.shape
                or not np.isfinite(image).all() or not np.isfinite(plane).all()):
            raise ValueError("invalid matrix or paired points")
        contour = None
        if polygon is not None:
            contour = np.asarray(polygon, dtype=np.float32)
            if (contour.ndim != 2 or contour.shape[1] != 2 or len(contour) < 3
                    or not np.isfinite(contour).all() or abs(cv2.contourArea(contour)) < 1e-6):
                raise ValueError("invalid calibration polygon")
        homogeneous = np.column_stack((image, np.ones(len(image)))) @ matrix.T
        denominator = homogeneous[:, 2]
        scales = np.linalg.norm(matrix[2]) * np.linalg.norm(np.column_stack((image, np.ones(len(image)))), axis=1)
        if np.any(np.abs(denominator) <= 1e-12 * scales):
            raise ValueError("check point maps near projective horizon")
        projected = homogeneous[:, :2] / denominator[:, None]
        if not np.isfinite(projected).all():
            raise ValueError("non-finite projection")
        errors = np.linalg.norm(projected - plane, axis=1)
        if not np.isfinite(errors).all():
            raise ValueError("non-finite check error")
        checks=[]
        for source, expected, actual, error in zip(image, plane, projected, errors):
            inside = None if contour is None else cv2.pointPolygonTest(contour, tuple(source), False) >= 0
            checks.append({"image":source.tolist(), "expected":expected.tolist(),
                           "projected":actual.tolist(), "error":float(error),
                           "inside_calibration_polygon":inside})
        return {"checks":checks, "points":len(checks),
                "rmse":float(np.sqrt(np.mean(errors ** 2))), "max_error":float(errors.max()),
                "scope":"Check-point residual in supplied plane units; independence and measurement quality are user responsibilities."}
    except (TypeError, ValueError, cv2.error, np.linalg.LinAlgError) as exc:
        raise ValueError("invalid calibration checks: " + str(exc)) from exc


def apply_calibration(config_path, camera_id, points_path, output_path):
    """Create a new config; resolve all source paths relative to the old config."""
    config_path = Path(config_path).expanduser().resolve()
    points_path = Path(points_path).expanduser().resolve()
    output_path = Path(output_path).expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    points_bytes = points_path.read_bytes()
    points = json.loads(points_bytes)
    result = fit_homography(points["image_points"], points["plane_points"])
    cameras = config.get("cameras")
    if not isinstance(cameras, list) or not all(isinstance(c, dict) for c in cameras):
        raise ValueError("invalid camera configuration")
    matches = [c for c in cameras if c.get("id") == camera_id]
    if len(matches) != 1:
        raise ValueError("camera must match exactly one entry")
    for camera in cameras:
        if not isinstance(camera.get("path"), str) or not camera["path"]:
            raise ValueError("invalid camera path")
        camera["path"] = str((config_path.parent / Path(camera["path"]).expanduser()).resolve())
        if "normalization_manifest" in camera:
            camera["normalization_manifest"]=str((config_path.parent / Path(camera["normalization_manifest"]).expanduser()).resolve())
    if points.get("coverage_polygon") is not None:
        from walkflows.multicamera_project import build_project
        project=build_project(config_path,allow_no_overlap=True)
        video=next(c["video"] for c in project["cameras"] if c["id"]==camera_id)
        result["calibration_polygon"]=validate_coverage_polygon(points["coverage_polygon"],result["calibration_polygon"],video["width"],video["height"])
    matches[0]["homography"] = result["homography"]
    matches[0]["calibration_polygon"] = result["calibration_polygon"]
    matches[0]["calibration_provenance"] = {
        "points_sha256": hashlib.sha256(points_bytes).hexdigest(),
        "points": result["points"], "rmse": result["rmse"], "max_error": result["max_error"],
        "scope": result["scope"]}
    content = json.dumps(config, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    with output_path.open("x", encoding="utf-8") as output:
        output.write(content)
    return result



def validate_coverage_polygon(points, hull, width, height):
    """Validate a simple user-drawn image-space polygon inside the fitted domain."""
    try:
        poly=np.asarray(points,dtype=np.float64)
        if (poly.ndim!=2 or poly.shape[1]!=2 or len(poly)<3 or not np.isfinite(poly).all()
                or len({tuple(p) for p in poly})!=len(poly)
                or abs(cv2.contourArea(poly.astype(np.float32)))<1e-6):
            raise ValueError("invalid coverage polygon")
        contour=np.asarray(hull,dtype=np.float32)
        for x,y in poly:
            if not (0<=x<width and 0<=y<height) or cv2.pointPolygonTest(contour,(float(x),float(y)),False)<0:
                raise ValueError("coverage polygon must be inside the calibration point hull")
        def cross(a,b,c):
            return float((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
        def intersects(a,b,c,d):
            def on(a,b,p):
                return (min(a[0],b[0])-1e-9<=p[0]<=max(a[0],b[0])+1e-9 and
                        min(a[1],b[1])-1e-9<=p[1]<=max(a[1],b[1])+1e-9)
            x1,x2,x3,x4=cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b)
            if x1*x2<0 and x3*x4<0:return True
            return any(abs(v)<=1e-9 and on(x,y,p) for v,x,y,p in
                       ((x1,a,b,c),(x2,a,b,d),(x3,c,d,a),(x4,c,d,b)))
        n=len(poly)
        for i in range(n):
            for j in range(i+1,n):
                if j==i+1 or (i==0 and j==n-1):continue
                if intersects(poly[i],poly[(i+1)%n],poly[j],poly[(j+1)%n]):
                    raise ValueError("coverage polygon cannot self-intersect")
        return poly.tolist()
    except (TypeError, ValueError, cv2.error) as exc:
        raise ValueError("invalid coverage polygon: "+str(exc)) from exc


def apply_calibration_bundle(config_path, bundle_path, output_path):
    """Validate and apply a complete multi-camera bundle to a new configuration."""
    from walkflows.multicamera_project import build_project
    config_path=Path(config_path).expanduser().resolve()
    bundle_path=Path(bundle_path).expanduser().resolve()
    output_path=Path(output_path).expanduser().resolve()
    raw=bundle_path.read_bytes()
    bundle=json.loads(raw)
    if not isinstance(bundle,dict) or bundle.get("schema_version") != 1 or not isinstance(bundle.get("cameras"),list):
        raise ValueError("invalid calibration bundle")
    project=build_project(config_path,allow_no_overlap=True)
    cameras=project["cameras"]
    entries=bundle["cameras"]
    if not all(isinstance(e,dict) and isinstance(e.get("id"),str) for e in entries):
        raise ValueError("invalid camera entries")
    by_id={e["id"]:e for e in entries}
    if len(by_id)!=len(entries) or set(by_id)!={c["id"] for c in cameras}:
        raise ValueError("bundle camera IDs must exactly match project cameras")
    config=json.loads(config_path.read_text(encoding="utf-8"))
    fitted={}
    for camera in cameras:
        entry=by_id[camera["id"]];video=camera["video"]
        if (entry.get("source_sha256") != video["sha256"] or
            entry.get("width") != video["width"] or entry.get("height") != video["height"]):
            raise ValueError("camera source or dimensions do not match: "+camera["id"])
        fit=fit_homography(entry.get("image_points"),entry.get("plane_points"))
        if entry.get("coverage_polygon") is not None:
            fit["calibration_polygon"]=validate_coverage_polygon(entry["coverage_polygon"],fit["calibration_polygon"],video["width"],video["height"])
        fitted[camera["id"]]=fit
    bundle_hash=hashlib.sha256(raw).hexdigest()
    for camera in config["cameras"]:
        camera["path"]=str((config_path.parent/Path(camera["path"]).expanduser()).resolve())
        if "normalization_manifest" in camera:
            camera["normalization_manifest"]=str((config_path.parent/Path(camera["normalization_manifest"]).expanduser()).resolve())
        fit=fitted[camera["id"]]
        camera["homography"]=fit["homography"]
        camera["calibration_polygon"]=fit["calibration_polygon"]
        camera["calibration_provenance"]={"points_sha256":bundle_hash,"points":fit["points"],
            "rmse":fit["rmse"],"max_error":fit["max_error"],"scope":fit["scope"]}
    content=json.dumps(config,indent=2,ensure_ascii=False,allow_nan=False)+"\n"
    with output_path.open("x",encoding="utf-8") as output:
        output.write(content)
    return {"cameras":len(fitted),"bundle_sha256":bundle_hash,
            "scope":"Maps require a shared measured coordinate system and independent validation."}
