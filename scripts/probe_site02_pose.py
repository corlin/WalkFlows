"""Full-clip pose research; ambiguous box matches are never assigned."""
from pathlib import Path
import csv,json,hashlib,collections,time
import cv2
from ultralytics import YOLO
r=Path(__file__).resolve().parents[1];w=r/"data/models/yolo11n-pose.pt"
expected="869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0"
assert hashlib.sha256(w.read_bytes()).hexdigest()==expected
out=r/"data/processed/site02-pose-full";out.mkdir(parents=True,exist_ok=True)
def iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/union if union>0 else 0
model=YOLO(str(w));summary=[]
expected_videos={"C0001001_v10":"9926ccdd05358cab83c292d9a62f2196961de9439e97857c592a75d2993d5276","C0001011_v10":"1d9b0ff0cbf92d9d107cfb7b197fe393fea5937f1245e5bc99b852e7137c694d"}
for camera in ["C0001001_v10","C0001011_v10"]:
    track_path=r/"data/processed/site02-gpu-conf010"/(camera+"_observations.csv")
    video_path=r/"data/raw/multiview/002_site02_gaze"/(camera+".mp4")
    video_sha=hashlib.sha256(video_path.read_bytes()).hexdigest()
    if video_sha!=expected_videos[camera]:raise ValueError("Video checksum mismatch")
    with track_path.open() as f:tracks=list(csv.DictReader(f))
    by_frame=collections.defaultdict(list)
    for row in tracks:by_frame[int(row["frame"])].append(row)
    cap=cv2.VideoCapture(str(r/"data/raw/multiview/002_site02_gaze"/(camera+".mp4")));rows=[];frames=[];pose_rows=[];n=0;start=time.perf_counter()
    while True:
        ok,image=cap.read()
        if not ok:break
        pred=model.predict(image[:,:896],device=0,conf=.1,imgsz=640,verbose=False)[0]
        boxes=pred.boxes.xyxy.cpu().tolist();scores=pred.boxes.conf.cpu().tolist()
        kpt=pred.keypoints.xy.cpu().tolist() if pred.keypoints is not None else []
        conf=pred.keypoints.conf.cpu().tolist() if pred.keypoints is not None and pred.keypoints.conf is not None else []
        for j,box in enumerate(boxes):
            pose_rows.append({"frame":n,"pose_index":j,"left":box[0],"top":box[1],"right":box[2],"bottom":box[3],"confidence":scores[j],"left_ankle_confidence":conf[j][15] if j<len(conf) else "","right_ankle_confidence":conf[j][16] if j<len(conf) else ""})
        frame_tracks=by_frame[n];tboxes=[[float(x[k]) for k in ["left","top","right","bottom"]] for x in frame_tracks]
        edges=[(i,j,iou(a,b)) for i,a in enumerate(tboxes) for j,b in enumerate(boxes) if iou(a,b)>=.5]
        tc=collections.Counter(i for i,j,d in edges);pc=collections.Counter(j for i,j,d in edges)
        matches={i:(j,d) for i,j,d in edges if tc[i]==1 and pc[j]==1}
        for i,track in enumerate(frame_tracks):
            row={"frame":n,"relative_s":n/15,"local_id":track["local_id"],"match_status":"unique" if i in matches else "ambiguous" if tc[i] else "no_candidate","pose_index":"","box_iou":"","pose_confidence":"","left_ankle_x":"","left_ankle_y":"","left_ankle_confidence":"","right_ankle_x":"","right_ankle_y":"","right_ankle_confidence":""}
            if i in matches:
                j,d=matches[i];row.update(pose_index=j,box_iou=d,pose_confidence=scores[j])
                if j<len(kpt) and j<len(conf):
                    row.update(left_ankle_x=kpt[j][15][0],left_ankle_y=kpt[j][15][1],left_ankle_confidence=conf[j][15],right_ankle_x=kpt[j][16][0],right_ankle_y=kpt[j][16][1],right_ankle_confidence=conf[j][16])
            rows.append(row)
        frames.append({"frame":n,"relative_s":n/15,"track_observations":len(frame_tracks),"pose_boxes":len(boxes),"unique_matches":len(matches),"unmatched_pose_boxes":len(boxes)-len(matches)})
        n+=1
    cap.release()
    if n!=218:raise ValueError("Unexpected frame count")
    for suffix,data in [("track_pose",rows),("frames",frames),("pose_boxes",pose_rows)]:
        with (out/(camera+"_"+suffix+".csv")).open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    counts=collections.Counter(row["match_status"] for row in rows)
    report={"camera":camera,"video_sha256":video_sha,"track_csv_sha256":hashlib.sha256(track_path.read_bytes()).hexdigest(),"frames":n,"track_observations":len(rows),"match_status":dict(counts),"seconds":time.perf_counter()-start};summary.append(report);print(json.dumps(report),flush=True)
(out/"summary.json").write_text(json.dumps({"weights_sha256":expected,"script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"source_metadata":"data/upstream-research/yolo11-model-tree.json","model_source":"Ultralytics/YOLO11","device":"cuda:0","confidence":.1,"imgsz":640,"iou_threshold":.5,"note":"Unique box overlap is a candidate correspondence, not confirmed identity. Keypoint confidence is not visibility truth or calibrated probability. No quality gate is changed.","cameras":summary},indent=2))
