"""One-frame, per-view conditional detector comparison on selected WILDTRACK inputs."""
import argparse
import hashlib
import json
import logging
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment
from ultralytics import YOLO
from ultralytics.utils import LOGGER


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def match_counts(detections, references, threshold):
    if not detections or not references:
        return 0
    a=np.asarray(detections,dtype=float)
    b=np.asarray(references,dtype=float)
    lo=np.maximum(a[:,None,:2],b[None,:,:2])
    hi=np.minimum(a[:,None,2:],b[None,:,2:])
    intersection=np.maximum(hi-lo,0).prod(axis=2)
    areas_a=np.maximum(a[:,2:]-a[:,:2],0).prod(axis=1)
    areas_b=np.maximum(b[:,2:]-b[:,:2],0).prod(axis=1)
    union=areas_a[:,None]+areas_b[None,:]-intersection
    iou=np.divide(intersection,union,out=np.zeros_like(intersection),where=union>0)
    valid=iou>=threshold
    cost=np.where(valid,-1000-iou,0)
    rows,cols=linear_sum_assignment(cost)
    return int(valid[rows,cols].sum())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory",type=Path,required=True)
    p.add_argument("--weights",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--device",default="cpu")
    args=p.parse_args()
    root=args.directory.resolve(strict=True)
    manifest=json.loads((root/"manifest.json").read_text())
    files={x["archive_path"].removeprefix("Wildtrack_dataset/"):x for x in manifest["files"]}
    required=["annotations_positions/00000000.json"]+[f"Image_subsets/C{i}/00000000.png" for i in range(1,7)]
    for name in required:
        if name not in files or sha(root/name)!=files[name]["sha256"]:
            raise ValueError("missing or modified input: "+name)
    weights=args.weights.resolve(strict=True);weights_hash=sha(weights)
    truth=json.loads((root/required[0]).read_text())
    model=YOLO(str(weights));results=[]
    class Warnings(logging.Handler):
        def __init__(self):
            super().__init__(logging.WARNING)
            self.messages=[]
        def emit(self, record):
            self.messages.append(record.getMessage())
    warnings=Warnings(); LOGGER.addHandler(warnings)
    warmup=cv2.imread(str(root/"Image_subsets/C1/00000000.png"))
    if warmup is None:raise ValueError("unreadable warmup")
    model.predict(warmup,classes=[0],conf=.25,imgsz=640,device=args.device,verbose=False)
    warmup_warnings=warnings.messages[:]; warnings.messages.clear()
    for camera in range(1,7):
        path=root/f"Image_subsets/C{camera}/00000000.png"
        image=cv2.imread(str(path))
        if image is None:raise ValueError("unreadable image: "+str(path))
        output=model.predict(image,classes=[0],conf=.25,imgsz=640,device=args.device,verbose=False)[0]
        boxes=output.boxes
        detected=boxes.xyxy.cpu().tolist() if boxes is not None else []
        truth_boxes=[]
        for person in truth:
            for view in person["views"]:
                if view["viewNum"]!=camera-1:continue
                box=[view["xmin"],view["ymin"],view["xmax"],view["ymax"]]
                if all(isinstance(x,(int,float)) for x in box) and box[0]>=0 and box[1]>=0 and box[2]>box[0] and box[3]>box[1]:
                    truth_boxes.append(box)
        matches=match_counts(detected,truth_boxes,.5)
        results.append({"camera":camera,"detections":len(detected),"reference_boxes":len(truth_boxes),
                        "iou50_one_to_one_matches":matches,
                        "unmatched_detections":len(detected)-matches,"unmatched_reference":len(truth_boxes)-matches})
    LOGGER.removeHandler(warnings)
    if sha(weights)!=weights_hash:raise ValueError("weights changed")
    report={"scope":"One annotated frame, selected six views, IoU 0.5; conditional comparison, not a benchmark or tracking evaluation.",
            "data_manifest_sha256":sha(root/"manifest.json"),"source_url":manifest["url"],"source_etag":manifest["etag"],
            "weights_sha256":weights_hash,"code_sha256":sha(Path(__file__)),"confidence":.25,"image_size":640,"device":args.device,
            "warmup_warnings":warmup_warnings,"evaluation_warnings":warnings.messages,"results":results}
    with args.output.open("x",encoding="utf-8") as f:json.dump(report,f,indent=2);f.write(chr(10))
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
