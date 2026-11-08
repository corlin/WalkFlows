"""Research diagnostic: independent detector vs saved tracker; no recall claims."""
from pathlib import Path
import csv,json,argparse,time
import cv2
from ultralytics import YOLO
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--imgsz",type=int,default=640)
parser.add_argument("--output",type=Path)
args=parser.parse_args()
out=args.output or root/"data/processed/site02-gap-diagnostic";out.mkdir(parents=True,exist_ok=True)
model=YOLO(str(root/"data/models/yolo11n.pt"));summary={}
for camera in ["C0001001_v10","C0001011_v10"]:
    frames=list(csv.DictReader((root/"data/processed/site02-gpu-conf010"/(camera+"_frames.csv")).open()))
    cap=cv2.VideoCapture(str(root/"data/raw/multiview/002_site02_gaze"/(camera+".mp4")))
    rows=[];index=0;samples=[];start=time.perf_counter()
    while True:
        ok,image=cap.read()
        if not ok:break
        left=image[:,:896].copy()
        result=model.predict(left,classes=[0],conf=.10,imgsz=args.imgsz,device=0,verbose=False)[0]
        scores=result.boxes.conf.cpu().tolist()
        tracked=int(frames[index]["tracked_boxes"])
        rows.append([index,index/15,len(scores),sum(s>=.25 for s in scores),max(scores,default=0),tracked])
        if camera=="C0001011_v10" and index in [0,15,26,40,82,100,210]:
            plot=result.plot();cv2.putText(plot,f"frame={index} raw={len(scores)} tracked={tracked}",(8,25),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,255),2)
            samples.append(cv2.resize(plot,(448,336)))
        index+=1
    cap.release();assert index==218
    with (out/(camera+"_detector_vs_tracker.csv")).open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["frame","relative_s","raw_count_conf010","raw_count_conf025","max_confidence","tracked_count"]);w.writerows(rows)
    zeros=[r for r in rows if r[5]==0]
    summary[camera]={"frames":index,"imgsz":args.imgsz,"elapsed_s":time.perf_counter()-start,"raw_positive_frames":sum(r[2]>0 for r in rows),"high_score_frames":sum(r[3]>0 for r in rows),"zero_track_frames":len(zeros),"zero_track_with_raw010":sum(r[2]>0 for r in zeros),"zero_track_with_raw025":sum(r[3]>0 for r in zeros),"zero_track_no_raw010":sum(r[2]==0 for r in zeros)}
    if samples:cv2.imwrite(str(out/"camera2-gap-contact-sheet.jpg"),cv2.hconcat(samples))
(out/"summary.json").write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
