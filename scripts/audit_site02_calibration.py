"""Audit calibration contracts only; deliberately emits no estimated person positions."""
from pathlib import Path
import csv,json,hashlib
import cv2
import numpy as np
r=Path(__file__).resolve().parents[1];assets=r/"data/upstream-research"
scene=json.loads((assets/"site02_scene01_v1.json").read_text())
report={"source_commit":"7e334db96ca7ab685628365a2eaa2d5e8117eac3","hist_aabb":scene["hist-aabb"],"cameras":[],"note":"Hull inclusion is a necessary calibration domain check, not floor accuracy or visible-foot evidence."}
for camera,transform in zip(scene["bcam-keys"],scene["bcam-transforms"]):
    path=assets/(camera+".json");cal=json.loads(path.read_text());sensor=cal["sensor0"]
    fmt=np.asarray(sensor["format"],dtype=float);scale=fmt/np.array([896,672]);assert np.isclose(scale[0],scale[1])
    coeff=np.asarray(sensor["A"]);assert coeff.shape==(2,45)
    hull=np.asarray(sensor["calib-hull"],dtype=np.float32)
    rows=list(csv.DictReader((r/"data/processed/site02-gpu-conf010"/(camera+"_observations.csv")).open()))
    points=[((float(x["left"])+float(x["right"]))/2,float(x["bottom"])) for x in rows]
    inside=[cv2.pointPolygonTest(hull,tuple(np.asarray(p)*scale),False)>=0 for p in points]
    report["cameras"].append({"camera":camera,"sensor_id":sensor["sensor-id"],"model":sensor["model"],"calibration_format":sensor["format"],"working_format":[896,672],"working_to_calibration_scale":scale.tolist(),"coeff_shape":list(coeff.shape),"baseline_m":cal["baseline"],"scene_rotation_norm":float(np.linalg.norm(transform["rotation"])),"observation_footpoints":len(points),"inside_calibration_hull":sum(inside),"outside_calibration_hull":len(points)-sum(inside),"calibration_sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
g=json.loads((r/"data/raw/multiview/002_site02_gaze/ground-truth.json").read_text())["track_results"]
assert g["frames"]==218
points=[p for t in g["tracks"] for p in t["path"]]
report["reference"]={"tracks":len(g["tracks"]),"points":len(points),"frames":g["frames"],"frame_range":[min(p[2] for p in points),max(p[2] for p in points)],"grid_shape":[g["width"],g["height"]],"hist_sz":g["hist-sz"],"top_left":g["top-left"],"grid_points_outside_shape":sum(not(0<=p[0]<g["width"] and 0<=p[1]<g["height"]) for p in points)}
out=r/"data/processed/site02-calibration-audit";out.mkdir(parents=True,exist_ok=True)
(out/"audit.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
