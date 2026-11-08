"""Cross-camera image-feature evidence without calibration optimization or new labels."""
from pathlib import Path
import cv2,json,subprocess
import numpy as np
from scipy.spatial.transform import Rotation
r=Path(__file__).resolve().parents[1];a=r/"data/upstream-research";out=r/"data/processed/site02-crossview-features";out.mkdir(parents=True,exist_ok=True)
scene=json.loads((a/"site02_scene01_v1.json").read_text());cameras=scene["bcam-keys"]
sensors=[json.loads((a/(camera+".json")).read_text())["sensor0"] for camera in cameras]
rot=[Rotation.from_quat(et["rotation"]).as_matrix() for et in scene["bcam-transforms"]];centers=[np.array(et["translation"]) for et in scene["bcam-transforms"]]
R=rot[1].T@rot[0];t=rot[1].T@(centers[0]-centers[1]);T=np.array([[0,-t[2],t[1]],[t[2],0,-t[0]],[-t[1],t[0],0]]);E=T@R
sift=cv2.SIFT_create(nfeatures=4000);matcher=cv2.BFMatcher(cv2.NORM_L2);rng=np.random.default_rng(0);reports=[]
def rays(points,sensor):
    conditioned=(points*np.array(sensor["format"])/[896,672]-sensor["center"])*sensor["scale"]
    text=subprocess.check_output([str(r/"data/processed/site02-native-lift/lift-probe")],input="".join(f"{x:.17g} {y:.17g}\n" for x,y in conditioned),text=True)
    terms=np.array([[float(v) for v in line.split()] for line in text.splitlines()]);uv=terms@np.array(sensor["A"]).T
    return np.column_stack([uv,np.ones(len(uv))])
def residual(x,y):
    ex=x@E.T;ety=y@E;n=np.sum(y*ex,axis=1)**2;d=ex[:,0]**2+ex[:,1]**2+ety[:,0]**2+ety[:,1]**2
    return np.sqrt(n/np.maximum(d,1e-30))
for frame in [0,90,180]:
    images=[]
    for camera in cameras:
        cap=cv2.VideoCapture(str(r/"data/raw/multiview/002_site02_gaze"/(camera+".mp4")));cap.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,image=cap.read();cap.release();assert ok;images.append(image[:,:896].copy())
    k0,d0=sift.detectAndCompute(cv2.cvtColor(images[0],cv2.COLOR_BGR2GRAY),None);k1,d1=sift.detectAndCompute(cv2.cvtColor(images[1],cv2.COLOR_BGR2GRAY),None)
    fwd=matcher.knnMatch(d0,d1,k=2);back=matcher.knnMatch(d1,d0,k=2)
    backward={m.queryIdx:m.trainIdx for pair in back if len(pair)==2 for m,n in [pair] if m.distance<.7*n.distance}
    matches=[m for pair in fwd if len(pair)==2 for m,n in [pair] if m.distance<.7*n.distance and backward.get(m.trainIdx)==m.queryIdx]
    accepted=[]
    for m in matches:
        points=[k0[m.queryIdx].pt,k1[m.trainIdx].pt]
        if all(cv2.pointPolygonTest(np.asarray(sensor["calib-hull"],dtype=np.float32),tuple(np.asarray(point)*np.array(sensor["format"])/[896,672]),False)>=0 for point,sensor in zip(points,sensors)):accepted.append(m)
    report={"frame":frame,"mutual_ratio_matches":len(matches),"inside_hulls":len(accepted)}
    if len(accepted)>=8:
        x=rays(np.array([k0[m.queryIdx].pt for m in accepted]),sensors[0]);y=rays(np.array([k1[m.trainIdx].pt for m in accepted]),sensors[1]);err=residual(x,y);null=[float(np.median(residual(x,y[rng.permutation(len(y))]))) for _ in range(100)]
        report.update({"median_normalized_sampson":float(np.median(err)),"p90_normalized_sampson":float(np.percentile(err,90)),"shuffle_median_of_medians":float(np.median(null)),"count_below_0003":int(np.sum(err<.003))})
    else:report["status"]="insufficient_unverified_matches"
    draw=cv2.drawMatches(images[0],k0,images[1],k1,accepted,None,flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS);cv2.imwrite(str(out/(f"frame{frame}_mutual_sift.jpg")),draw)
    reports.append(report)
result={"scope":"Image feature consistency under supplied scene extrinsics. Matches are unlabelled hypotheses, shuffle control is descriptive, not a significance test. No parameter fit, identity or synchronization validation.","SIFT_ratio":.7,"frames":reports}
(out/"summary.json").write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
