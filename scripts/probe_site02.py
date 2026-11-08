"""Research probe: left-eye local tracking only; no floor/global identity claims."""
import argparse
import csv
import hashlib
import json
import time
from pathlib import Path
import cv2
import torch
from ultralytics import YOLO

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--conf",type=float,default=.25)
    parser.add_argument("--imgsz",type=int,default=640)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args(); root=args.root
    if not 0 < args.conf < 1: parser.error("conf must be between 0 and 1")
    weights=root/"data/models/yolo11n.pt"
    if not weights.is_file(): parser.error("Missing pretrained weights")
    out=args.output or root/"data/processed/site02-gpu-probe";out.mkdir(parents=True,exist_ok=True)
    expected={"C0001001_v10":"9926ccdd05358cab83c292d9a62f2196961de9439e97857c592a75d2993d5276","C0001011_v10":"1d9b0ff0cbf92d9d107cfb7b197fe393fea5937f1245e5bc99b852e7137c694d"}
    meta={"torch":torch.__version__,"cuda":torch.version.cuda,"gpu":torch.cuda.get_device_name(0),"weights_sha256":sha(weights),"imgsz":args.imgsz,"conf":args.conf,"tracker":"bytetrack.yaml","note":"Local left-eye tracks only; IDs are not customers. No validated recall, floor position or cross-camera identity.","runs":[],"missing":[]}
    for camera,digest in expected.items():
        src=root/"data/raw/multiview/002_site02_gaze"/(camera+".mp4")
        if not src.is_file():meta["missing"].append(camera);continue
        if sha(src)!=digest:raise ValueError("Source checksum mismatch: "+camera)
        cap=cv2.VideoCapture(str(src));fps=cap.get(cv2.CAP_PROP_FPS)
        if not cap.isOpened() or fps<=0:raise ValueError("Invalid video")
        model=YOLO(str(weights));rows=[];frames=[];ids=set();n=0;start=time.perf_counter()
        writer=cv2.VideoWriter(str(out/(camera+"_left_tracked.mp4")),cv2.VideoWriter_fourcc(*"mp4v"),fps,(896,672))
        if not writer.isOpened():raise RuntimeError("Cannot open writer")
        try:
            while True:
                ok,frame=cap.read()
                if not ok:break
                if frame.shape[:2]!=(672,1792):raise ValueError("Unexpected stereo dimensions")
                left=frame[:,:896].copy()
                result=model.track(left,persist=True,tracker="bytetrack.yaml",classes=[0],conf=args.conf,imgsz=args.imgsz,device=0,verbose=False)[0]
                boxes=result.boxes; tracked=0
                if boxes is not None and boxes.id is not None:
                    for box,tid,conf in zip(boxes.xyxy.cpu().tolist(),boxes.id.cpu().tolist(),boxes.conf.cpu().tolist()):
                        rows.append([n,n/fps,int(tid),conf,*box]);ids.add(int(tid));tracked+=1
                frames.append([n,n/fps,0 if boxes is None else len(boxes),tracked])
                writer.write(result.plot());n+=1
        finally:cap.release();writer.release()
        torch.cuda.synchronize()
        for suffix,header,records in [("frames",["frame","relative_s","returned_boxes","tracked_boxes"],frames),("observations",["frame","relative_s","local_id","confidence","left","top","right","bottom"],rows)]:
            with (out/(camera+"_"+suffix+".csv")).open("w",newline="") as f:
                w=csv.writer(f);w.writerow(header);w.writerows(records)
        run={"camera":camera,"sha256":digest,"frames":n,"fps":fps,"observations":len(rows),"local_ids":len(ids),"zero_track_frames":sum(r[3]==0 for r in frames),"elapsed_s":time.perf_counter()-start,"expected_frames":218}
        meta["runs"].append(run);print(json.dumps(run),flush=True)
        (out/"run.json").write_text(json.dumps(meta,indent=2))
    (out/"run.json").write_text(json.dumps(meta,indent=2))

if __name__=="__main__":main()
