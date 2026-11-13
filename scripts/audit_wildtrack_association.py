"""Conditional WILDTRACK cross-view proximity diagnostic on fixed annotated frames."""
import argparse
import hashlib
import json
import logging
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment
from ultralytics import YOLO
from ultralytics.utils import LOGGER


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidates(left,right,distance):
    if not math.isfinite(distance) or distance<=0:raise ValueError("invalid distance")
    edges=[];left_count={};right_count={}
    for a in left:
        for b in right:
            d=math.hypot(a["x"]-b["x"],a["y"]-b["y"])
            if d<=distance:
                edges.append((a,b,d))
                left_count[a["id"]]=left_count.get(a["id"],0)+1
                right_count[b["id"]]=right_count.get(b["id"],0)+1
    unique=[];ambiguous=[]
    for a,b,d in edges:
        (unique if left_count[a["id"]]==1 and right_count[b["id"]]==1 else ambiguous).append((a,b,d))
    return unique,ambiguous


def evaluate_pairs(left,right,distance):
    unique,ambiguous=candidates(left,right,distance)
    eligible={p["reference"] for p in left if p["reference"] is not None} & {
        p["reference"] for p in right if p["reference"] is not None}
    correct=incorrect=unknown=0
    for a,b,_ in unique:
        if a["reference"] is None or b["reference"] is None:unknown+=1
        elif a["reference"]==b["reference"]:correct+=1
        else:incorrect+=1
    return {"unique":len(unique),"ambiguous_edges":len(ambiguous),
            "supported_correct":correct,"supported_incorrect":incorrect,"unknown":unknown,
            "eligible_same_id":len(eligible)}


def assign_references(boxes,truth):
    if not boxes or not truth:return {}
    a=np.asarray(boxes,dtype=float);b=np.asarray([x["box"] for x in truth],dtype=float)
    low=np.maximum(a[:,None,:2],b[None,:,:2]);high=np.minimum(a[:,None,2:],b[None,:,2:])
    intersection=np.maximum(high-low,0).prod(axis=2)
    area_a=np.maximum(a[:,2:]-a[:,:2],0).prod(axis=1)
    area_b=np.maximum(b[:,2:]-b[:,:2],0).prod(axis=1)
    union=area_a[:,None]+area_b[None,:]-intersection
    overlap=np.divide(intersection,union,out=np.zeros_like(intersection),where=union>0)
    valid=overlap>=.5;rows,cols=linear_sum_assignment(np.where(valid,-1000-overlap,0))
    return {int(i):truth[int(j)]["id"] for i,j in zip(rows,cols) if valid[i,j]}


def inverse_ground(intrinsic,extrinsic):
    source=cv2.FileStorage(str(intrinsic),cv2.FILE_STORAGE_READ)
    try:matrix=source.getNode("camera_matrix").mat()
    finally:source.release()
    root=ET.parse(extrinsic).getroot()
    r=np.fromstring(root.find("rvec").text,sep=" ")
    t=np.fromstring(root.find("tvec").text,sep=" ")
    if matrix is None or matrix.shape!=(3,3) or r.shape!=(3,) or t.shape!=(3,):
        raise ValueError("invalid calibration")
    rotation,_=cv2.Rodrigues(r)
    return np.linalg.inv(matrix@np.column_stack((rotation[:,0],rotation[:,1],t)))


def verified(root,manifest_name,names):
    manifest_path=root/"manifest.json"
    manifest=json.loads(manifest_path.read_text())
    members={e["archive_path"].removeprefix("Wildtrack_dataset/"):e for e in manifest["files"]}
    for name in names:
        if name not in members or sha(root/name)!=members[name]["sha256"]:
            raise ValueError("missing or modified "+manifest_name+" input: "+name)
    return manifest_path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images",required=True,type=Path);parser.add_argument("--calibration",required=True,type=Path)
    parser.add_argument("--weights",required=True,type=Path);parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--device",default="cpu")
    args=parser.parse_args()
    images=args.images.resolve(strict=True);calibration=args.calibration.resolve(strict=True)
    frames=(0,500,1000,1500,1995);camera_names=("CVLab1","CVLab2","CVLab3","CVLab4","IDIAP1","IDIAP2")
    image_names=[f"annotations_positions/{frame:08d}.json" for frame in frames]
    image_names += [f"Image_subsets/C{cam}/{frame:08d}.png" for frame in frames for cam in range(1,7)]
    calib_names=[f"calibrations/{typ}/{prefix}_{cam}.xml" for cam in camera_names
                 for typ,prefix in (("intrinsic_zero","intr"),("extrinsic","extr"))]
    image_manifest=verified(images,"images",image_names)
    calibration_manifest=verified(calibration,"calibration",calib_names)
    transforms=[inverse_ground(calibration/f"calibrations/intrinsic_zero/intr_{name}.xml",
                               calibration/f"calibrations/extrinsic/extr_{name}.xml") for name in camera_names]
    weights=args.weights.resolve(strict=True);weight_hash=sha(weights)
    class Warnings(logging.Handler):
        def __init__(self):super().__init__(logging.WARNING);self.messages=[]
        def emit(self,record):self.messages.append(record.getMessage())
    warnings=Warnings();LOGGER.addHandler(warnings);model=YOLO(str(weights))
    sample=cv2.imread(str(images/"Image_subsets/C1/00000000.png"))
    if sample is None:raise ValueError("unreadable warmup")
    model.predict(sample,classes=[0],conf=.25,imgsz=640,device=args.device,verbose=False)
    warmup_warnings=warnings.messages[:];warnings.messages.clear()
    output=[]
    for frame in frames:
        annotations=json.loads((images/f"annotations_positions/{frame:08d}.json").read_text())
        per_camera=[]
        for camera in range(1,7):
            image=cv2.imread(str(images/f"Image_subsets/C{camera}/{frame:08d}.png"))
            if image is None:raise ValueError("unreadable frame")
            prediction=model.predict(image,classes=[0],conf=.25,imgsz=640,device=args.device,verbose=False)[0]
            boxes=prediction.boxes.xyxy.cpu().tolist() if prediction.boxes is not None else []
            truth=[]
            for person in annotations:
                for view in person["views"]:
                    if view["viewNum"]!=camera-1:continue
                    box=[view["xmin"],view["ymin"],view["xmax"],view["ymax"]]
                    if min(box[:2])>=0 and box[2]>box[0] and box[3]>box[1]:
                        truth.append({"box":box,"id":person["personID"]})
            labels=assign_references(boxes,truth)
            points=[]
            for i,box in enumerate(boxes):
                ray=transforms[camera-1]@np.array([(box[0]+box[2])/2,box[3],1.])
                if not np.isfinite(ray).all() or abs(ray[2])<1e-12:continue
                xy=ray[:2]/ray[2]/100
                if not np.isfinite(xy).all():continue
                points.append({"id":str(i),"x":float(xy[0]),"y":float(xy[1]),"reference":labels.get(i)})
            per_camera.append(points)
        pairs=[]
        for i in range(6):
            for j in range(i+1,6):
                pairs.append({"left":i+1,"right":j+1,**evaluate_pairs(per_camera[i],per_camera[j],.5)})
        output.append({"frame":frame,"detections_with_projection":[len(x) for x in per_camera],"pairs":pairs})
        print("completed frame",frame,flush=True)
    LOGGER.removeHandler(warnings)
    if sha(weights)!=weight_hash:raise ValueError("weights changed")
    verified(images,"images",image_names);verified(calibration,"calibration",calib_names)
    report={"scope":"Single-frame spatial proximity between untracked detections; IoU-linked labels are conditional, unknown detections retained. Not a tracker, identity or physical accuracy benchmark.",
            "image_manifest_sha256":sha(image_manifest),"calibration_manifest_sha256":sha(calibration_manifest),
            "weights_sha256":weight_hash,"code_sha256":sha(Path(__file__)),
            "parameters":{"fps_assumption":None,"iou":.5,"distance_m":.5,"confidence":.25,"image_size":640},
            "warmup_warnings":warmup_warnings,"evaluation_warnings":warnings.messages,"frames":output}
    with args.output.open("x",encoding="utf-8") as f:json.dump(report,f,indent=2,allow_nan=False);f.write(chr(10))


if __name__=="__main__":
    main()
