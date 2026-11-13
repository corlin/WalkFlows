"""Sample raw person detections from a generic project for diagnostic review."""
import argparse
import json
import math
from pathlib import Path

import cv2
from ultralytics import YOLO, __version__ as ultralytics_version

from walkflows.multicamera_processing import file_sha256
from walkflows.multicamera_project import build_project


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",required=True,type=Path)
    parser.add_argument("--weights",required=True,type=Path,action="append")
    parser.add_argument("--frame",required=True,type=int,action="append")
    parser.add_argument("--confidence",type=float,default=0.1)
    parser.add_argument("--device",default="cpu")
    parser.add_argument("--image-size",type=int,default=640)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if not 0 < args.confidence <= 1 or not math.isfinite(args.confidence):
        raise ValueError("invalid confidence")
    if args.image_size < 32 or args.image_size > 4096 or args.image_size % 32:
        raise ValueError("image size must be a multiple of 32 between 32 and 4096")
    if len(set(args.frame)) != len(args.frame) or any(f < 0 for f in args.frame):
        raise ValueError("frames must be unique and non-negative")
    project=build_project(args.config)
    if any(max(args.frame) >= c["video"]["frame_count"] for c in project["cameras"]):
        raise ValueError("frame outside declared video length")
    if args.output.exists():
        raise FileExistsError(args.output)
    models=[]
    for weights in args.weights:
        weights=weights.expanduser().resolve(strict=True)
        models.append((weights,file_sha256(weights),YOLO(str(weights))))
    results=[]
    for camera in project["cameras"]:
        source=camera["video"]
        if file_sha256(source["path"]) != source["sha256"]:
            raise ValueError("video hash changed")
        cap=cv2.VideoCapture(source["path"])
        try:
            for frame in sorted(args.frame):
                if not cap.set(cv2.CAP_PROP_POS_FRAMES,frame):
                    raise ValueError("video seek failed")
                ok,image=cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != frame+1:
                    raise ValueError("cannot verify decoded frame index")
                roi=camera.get("analysis_roi")
                x,y,w,h=roi if roi else (0,0,source["width"],source["height"])
                image=image[y:y+h,x:x+w]
                for path,digest,model in models:
                    result=model.predict(image,conf=args.confidence,classes=[0],device=args.device,
                                         imgsz=args.image_size,verbose=False)[0]
                    boxes=result.boxes
                    detections=[]
                    if boxes is not None:
                        for box,score in zip(boxes.xyxy.cpu().tolist(),boxes.conf.cpu().tolist()):
                            left,top,right,bottom=box
                            detections.append({"box":[left+x,top+y,right+x,bottom+y],"confidence":score})
                    results.append({"camera":camera["id"],"frame":frame,"weight_sha256":digest,
                                    "detections":detections})
        finally:cap.release()
        if file_sha256(source["path"]) != source["sha256"]:
            raise ValueError("video changed during probe")
    if any(file_sha256(path)!=digest for path,digest,_ in models):
        raise ValueError("weights changed during probe")
    report={"scope":"Raw sampled detections, not tracking, visibility truth, recall or physical accuracy.",
            "project":project,"model_weights":[{"path":str(p),"sha256":h} for p,h,_ in models],
            "frames":sorted(args.frame),"confidence":args.confidence,"image_size":args.image_size,"device":args.device,
            "opencv":cv2.__version__,"ultralytics":ultralytics_version,
            "script_sha256":file_sha256(__file__),"results":results}
    content=json.dumps(report,indent=2,allow_nan=False)
    with args.output.open("x",encoding="utf-8") as file:file.write(content+"\n")
    print(json.dumps({"sampled_camera_frames":len(project["cameras"])*len(args.frame),
                      "models":len(models),"output":str(args.output.resolve())}))


if __name__=="__main__":
    main()
