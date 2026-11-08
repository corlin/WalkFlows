"""Automatic stereo correspondences; extrinsic conventions tested as hypotheses only."""
from pathlib import Path
import cv2,csv,json,subprocess
import numpy as np
from scipy.spatial.transform import Rotation
r=Path(__file__).resolve().parents[1];a=r/"data/upstream-research";out=r/"data/processed/site02-stereo-check";out.mkdir(parents=True,exist_ok=True)
orb=cv2.ORB_create(nfeatures=2500);matcher=cv2.BFMatcher(cv2.NORM_HAMMING);records=[]
def undistort(points,sensor):
    conditioned=(points*np.array(sensor["format"])/[896,672]-sensor["center"])*sensor["scale"]
    output=subprocess.check_output([str(r/"data/processed/site02-native-lift/lift-probe")],input="".join(f"{x:.17g} {y:.17g}\n" for x,y in conditioned),text=True)
    terms=np.array([[float(v) for v in line.split()] for line in output.splitlines()]);uv=terms@np.array(sensor["A"]).T
    return np.column_stack([uv,np.ones(len(uv))])
def sampson(x,y,E):
    ex=x@E.T;ety=y@E;num=np.sum(y*ex,axis=1)**2;den=ex[:,0]**2+ex[:,1]**2+ety[:,0]**2+ety[:,1]**2
    return np.sqrt(num/np.maximum(den,1e-30))
for camera in ["C0001001_v10","C0001011_v10"]:
    cal=json.loads((a/(camera+".json")).read_text());axis=np.array(cal["rotation-axis"]);R=Rotation.from_rotvec(axis*cal["rotation-angle"]).as_matrix();t=np.array(cal["t"])
    T=np.array([[0,-t[2],t[1]],[t[2],0,-t[0]],[-t[1],t[0],0]])
    hypotheses={"TxR":T@R,"RTx":R@T,"TxRinv":T@R.T,"RinvTx":R.T@T}
    cap=cv2.VideoCapture(str(r/"data/raw/multiview/002_site02_gaze"/(camera+".mp4")))
    for frame in [0,45,90,135,180]:
        cap.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,image=cap.read();assert ok
        left,right=image[:,:896],image[:,896:]
        ka,da=orb.detectAndCompute(cv2.cvtColor(left,cv2.COLOR_BGR2GRAY),None);kb,db=orb.detectAndCompute(cv2.cvtColor(right,cv2.COLOR_BGR2GRAY),None)
        forward=matcher.knnMatch(da,db,k=2);reverse=matcher.knnMatch(db,da,k=2)
        back={m.queryIdx:m.trainIdx for pair in reverse if len(pair)==2 for m,n in [pair] if m.distance<.75*n.distance}
        matches=[m for pair in forward if len(pair)==2 for m,n in [pair] if m.distance<.75*n.distance and back.get(m.trainIdx)==m.queryIdx]
        pairs=np.array([[ka[m.queryIdx].pt,kb[m.trainIdx].pt] for m in matches])
        for order in ["left_sensor0","left_sensor1"]:
            sensors=[cal["sensor0"],cal["sensor1"]] if order=="left_sensor0" else [cal["sensor1"],cal["sensor0"]]
            mask=[]
            for pa,pb in pairs:
                mask.append(all(cv2.pointPolygonTest(np.array(s["calib-hull"],dtype=np.float32),tuple(point*np.array(s["format"])/[896,672]),False)>=0 for point in [pa,pb] for s in [cal["sensor0"],cal["sensor1"]]))
            points=pairs[np.array(mask)];assert len(points)>=8
            x=undistort(points[:,0],sensors[0]);y=undistort(points[:,1],sensors[1])
            for name,E in hypotheses.items():
                residual=sampson(x,y,E)
                records.append({"camera":camera,"frame":frame,"sensor_order_hypothesis":order,"extrinsic_hypothesis":name,"descriptor_mutual_matches":len(matches),"in_calibration_hulls":len(points),"median_normalized_sampson":float(np.median(residual)),"p90_normalized_sampson":float(np.percentile(residual,90))})
        if frame==0:
            draw=cv2.drawMatches(left,ka,right,kb,matches[:50],None,flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS);cv2.imwrite(str(out/(camera+"_mutual_orb.jpg")),draw)
    cap.release()
with (out/"hypotheses.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
summary=[]
for camera in ["C0001001_v10","C0001011_v10"]:
 for order in ["left_sensor0","left_sensor1"]:
  for name in hypotheses:
   group=[x for x in records if x["camera"]==camera and x["sensor_order_hypothesis"]==order and x["extrinsic_hypothesis"]==name]
   summary.append({"camera":camera,"order":order,"extrinsic":name,"median_of_frame_medians":float(np.median([x["median_normalized_sampson"] for x in group]))})
report={"scope":"Automatic static-feature stereo epipolar consistency. No manual labels, no optimized calibration. Hypotheses do not establish upstream convention, floor accuracy or inter-camera synchronization.","frames_per_camera":[0,45,90,135,180],"summaries":summary}
(out/"summary.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
