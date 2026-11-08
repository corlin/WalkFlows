"""Numerical inverse distortion of supplied reference; qualitative overlay only."""
from pathlib import Path
import csv,json,collections
import cv2
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares
r=Path(__file__).resolve().parents[1];a=r/"data/upstream-research";out=r/"data/processed/site02-reference-overlay";out.mkdir(parents=True,exist_ok=True)
scene=json.loads((a/"site02_scene01_v1.json").read_text())
with (r/"data/processed/site02-reference-floor/reference_floor.csv").open() as f:reference=list(csv.DictReader(f))
exponents=np.array([(d-j,j) for d in range(8,-1,-1) for j in range(d+1)])
report={"scope":"Supplied reference projected through experimental model using numerical inverse, not upstream distortion cache. No new labels; identity correspondence to longest local track is a hypothesis.","cameras":[]}
for cam,et in zip(scene["bcam-keys"],scene["bcam-transforms"]):
    sensor=json.loads((a/(cam+".json")).read_text())["sensor0"];A=np.asarray(sensor["A"]);scale=np.array(sensor["format"])/[896,672];center=np.array(sensor["center"])
    rotation=Rotation.from_quat(et["rotation"]);C=np.array(et["translation"])
    def undistort(pixel):
        xy=(pixel*scale-center)*sensor["scale"]
        terms=xy[0]**exponents[:,0]*xy[1]**exponents[:,1]
        return A@terms
    with (r/"data/processed/site02-roi-review"/(cam+"_domain_observations.csv")).open() as f:obs=[row for row in csv.DictReader(f) if row["domain_status"]=="candidate_in_domain"]
    primary=collections.Counter(row["local_id"] for row in obs).most_common(1)[0][0];observed={int(row["frame"]):row for row in obs if row["local_id"]==primary}
    with (r/"data/processed/site02-gpu-conf010"/(cam+"_observations.csv")).open() as f:boxes=list(csv.DictReader(f))
    records=[];targets=[];previous=np.array([448.,336.]);tiles=[];cap=cv2.VideoCapture(str(r/"data/raw/multiview/002_site02_gaze"/(cam+".mp4")))
    for row in reference:
        frame=int(row["clip_frame"]);world=np.array([float(row["floor_x"]),float(row["floor_y"]),0.]);local=rotation.inv().apply(world-C)
        assert local[2]>0
        target=local[:2]/local[2];targets.append(target)
        solved=least_squares(lambda p:undistort(p)-target,previous,bounds=([0.,0.],[895.999,671.999]),xtol=1e-12,ftol=1e-12,gtol=1e-12)
        pixel=solved.x;error=float(np.linalg.norm(undistort(pixel)-target));inside=cv2.pointPolygonTest(np.asarray(sensor["calib-hull"],dtype=np.float32),tuple(pixel*scale),False)>=0
        valid=bool(solved.success and error<1e-8 and inside);previous=pixel
        dx=dy=None
        if frame in observed:
            ob=observed[frame];dx=float(pixel[0]-float(ob["pixel_x"]));dy=float(pixel[1]-float(ob["pixel_y"]))
        records.append({"frame":frame,"reference_pixel_x":float(pixel[0]),"reference_pixel_y":float(pixel[1]),"normalized_inverse_residual":error,"inside_hull":inside,"valid_numerical_inverse":valid,"hypothesis_local_id":primary,"reference_minus_box_x_px":dx,"reference_minus_box_y_px":dy})
        if frame in [0,60,120,180]:
            cap.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,image=cap.read();assert ok;image=image[:,:896].copy()
            for box in boxes:
                if int(box["frame"])!=frame:continue
                left,top,right,bottom=[int(float(box[k])) for k in ["left","top","right","bottom"]];cv2.rectangle(image,(left,top),(right,bottom),(0,180,0),2);cv2.circle(image,((left+right)//2,bottom),4,(0,180,0),-1)
            if valid:cv2.drawMarker(image,tuple(np.rint(pixel).astype(int)),(255,0,255),cv2.MARKER_CROSS,24,3)
            cv2.putText(image,'REFERENCE projection; frame '+str(frame),(10,28),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,0,255),2);tiles.append(cv2.resize(image,(672,504)))
    cap.release()
    with (out/(cam+"_reference_pixels.csv")).open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    cv2.imwrite(str(out/(cam+"_reference_overlay.jpg")),cv2.vconcat([cv2.hconcat(tiles[:2]),cv2.hconcat(tiles[2:])]))
    comparable=[x for x in records if x["valid_numerical_inverse"] and x["reference_minus_box_y_px"] is not None]
    pixel_array=np.array([[row["reference_pixel_x"],row["reference_pixel_y"]] for row in records])
    conditioned=(pixel_array*scale-center)*sensor["scale"]
    native_text=__import__("subprocess").check_output([str(r/"data/processed/site02-native-lift/lift-probe")],input="".join(f"{x:.17g} {y:.17g}\n" for x,y in conditioned),text=True)
    native_terms=np.array([[float(v) for v in line.split()] for line in native_text.splitlines()])
    native_residual=float(np.max(np.linalg.norm(native_terms@A.T-np.asarray(targets),axis=1)))
    assert native_residual<1e-8
    report["cameras"].append({"camera":cam,"reference_points":len(records),"valid_inverse":sum(x["valid_numerical_inverse"] for x in records),"max_native_forward_residual":native_residual,"max_normalized_inverse_residual":max(x["normalized_inverse_residual"] for x in records),"hypothesis_local_id":primary,"comparable_points":len(comparable),"median_reference_minus_box_dx_px":float(np.median([x["reference_minus_box_x_px"] for x in comparable])),"median_reference_minus_box_dy_px":float(np.median([x["reference_minus_box_y_px"] for x in comparable]))})
(out/"summary.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
