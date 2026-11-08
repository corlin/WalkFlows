"""Experimental source-aligned left-eye ray/ground intersection; not validated localization."""
from pathlib import Path
import csv,json,subprocess
import cv2
import numpy as np
from scipy.spatial.transform import Rotation
r=Path(__file__).resolve().parents[1];assets=r/"data/upstream-research"
scene=json.loads((assets/"site02_scene01_v1.json").read_text())
out=r/"data/processed/site02-floor-probe";out.mkdir(parents=True,exist_ok=True)
binary=r/"data/processed/site02-native-lift/lift-probe"
if not binary.is_file():raise RuntimeError("Run scripts/probe_native_lift.py first")
summary={"scope":"Experimental box-bottom ground intersections; no independently validated calibration, foot visibility, sync or global identity.","cameras":[]}
for camera,et in zip(scene["bcam-keys"],scene["bcam-transforms"]):
    assert et["scale"]==1 and scene["global-transformation"]=={"translation":[0,0,0],"rotation":[0,0,0,1],"scale":1.0}
    sensor=json.loads((assets/(camera+".json")).read_text())["sensor0"]
    with (r/"data/processed/site02-gpu-conf010"/(camera+"_observations.csv")).open() as f:obs=list(csv.DictReader(f))
    pixels=np.array([[(float(o["left"])+float(o["right"]))/2,float(o["bottom"])] for o in obs])
    scale=np.array(sensor["format"])/[896,672];C=np.array(et["translation"]);q=np.array(et["rotation"])
    assert abs(np.linalg.norm(q)-1)<1e-6
    rotation=Rotation.from_quat(q)
    def project(points):
        conditioned=(points*scale-np.array(sensor["center"]))*sensor["scale"]
        output=subprocess.check_output([str(binary)],input="".join(f"{x:.17g} {y:.17g}\n" for x,y in conditioned),text=True)
        terms=np.array([[float(v) for v in line.split()] for line in output.splitlines()])
        uv=terms@np.asarray(sensor["A"]).T
        local=np.column_stack([uv,np.ones(len(uv))])
        rays=rotation.apply(local)
        # Independent unit-quaternion vector formula cross-check.
        v=q[:3];ham=local+2*np.cross(v,np.cross(v,local)+q[3]*local)
        np.testing.assert_allclose(rays,ham,atol=1e-12)
        with np.errstate(divide="ignore",invalid="ignore"):
            t=-C[2]/rays[:,2];world=C+t[:,None]*rays
        return world,t,rays
    world,t,rays=project(pixels);shifted,_,_=project(pixels+[0,5])
    hull=np.asarray(sensor["calib-hull"],dtype=np.float32);bounds=scene["hist-aabb"]
    rows=[]
    for i,o in enumerate(obs):
        inside=cv2.pointPolygonTest(hull,tuple(pixels[i]*scale),False)>=0
        finite=bool(np.isfinite(world[i]).all());forward=bool(t[i]>0 and abs(rays[i,2])>1e-8)
        in_scene=bool(finite and bounds[0]<=world[i,0]<=bounds[2] and bounds[1]<=world[i,1]<=bounds[3])
        sensitivity=float(np.linalg.norm(shifted[i,:2]-world[i,:2]))
        rows.append([int(o["frame"]),o["local_id"],*pixels[i],*world[i],int(inside),int(forward),int(in_scene),sensitivity])
    with (out/(camera+"_experimental_floor.csv")).open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["frame","local_id","pixel_x","pixel_y","experimental_x","experimental_y","experimental_z","inside_calibration_hull","forward_nonparallel","in_scene_bounds","floor_shift_for_plus5px_y_m"]);w.writerows(rows)
    valid=[x for x in rows if x[7] and x[8] and x[9]]
    summary["cameras"].append({"camera":camera,"observations":len(rows),"inside_hull":sum(x[7] for x in rows),"forward_nonparallel":sum(x[8] for x in rows),"inside_scene":sum(x[9] for x in rows),"all_geometry_gates":len(valid),"median_shift_plus5px_m":float(np.median([x[10] for x in valid])) if valid else None,"max_plane_residual":float(np.nanmax(np.abs(world[:,2])))})
(out/"summary.json").write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
