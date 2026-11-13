"""Inspect inverse projections of reference points; this does not establish visibility."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from walkflows.multicamera_processing import file_sha256
from walkflows.multicamera_project import build_project
from walkflows.reference_eval import convert_reference


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",required=True,type=Path)
    parser.add_argument("--reference",required=True,type=Path)
    parser.add_argument("--frame",type=int,required=True)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    project=build_project(args.config)
    ref=json.loads(args.reference.read_text(encoding="utf-8"))["track_results"]
    reference=convert_reference(ref)
    if ref.get("start-frame")!=0 or args.frame not in reference["by_frame"]:
        raise ValueError("unsupported reference frame")
    if args.output.exists():raise FileExistsError(args.output)
    entries=[]
    for camera in project["cameras"]:
        video=camera["video"]
        if camera["offset_seconds"]!=0 or not np.isclose(1/video["fps"],reference["frame_duration"],rtol=1e-5,atol=1e-7):
            raise ValueError("frame alignment assumption does not match metadata")
        if camera["homography"] is None or camera["calibration_polygon"] is None:
            raise ValueError("mapping and calibration polygon required")
        matrix=np.linalg.inv(np.asarray(camera["homography"],float))
        polygon=np.asarray(camera["calibration_polygon"],np.float32)
        roi=camera.get("analysis_roi") or [0,0,video["width"],video["height"]]
        for point in reference["by_frame"][args.frame]:
            value=matrix@np.array([point["x"],point["y"],1.0])
            if not np.isfinite(value).all() or abs(value[2])<1e-9:
                entries.append({"camera":camera["id"],"reference_id":point["id"],"status":"undefined"})
                continue
            x,y=(value[:2]/value[2]).tolist()
            inside=(roi[0]<=x<roi[0]+roi[2] and roi[1]<=y<roi[1]+roi[3] and
                    cv2.pointPolygonTest(polygon,(x,y),False)>=0)
            entries.append({"camera":camera["id"],"reference_id":point["id"],"image_point":[x,y],
                            "status":"inside_calibrated_domain" if inside else "outside_or_extrapolation_unknown"})
    report={"scope":"Inverse projection is a geometric diagnostic only, not camera visibility or verified person location; "
                    "outside-domain extrapolations may be inaccurate.",
            "frame":args.frame,"config_sha256":file_sha256(args.config),
            "reference_sha256":file_sha256(args.reference),"script_sha256":file_sha256(__file__),
            "entries":entries}
    with args.output.open("x",encoding="utf-8") as file:json.dump(report,file,indent=2,allow_nan=False)
    print(json.dumps({"entries":len(entries),"inside":sum(x["status"]=="inside_calibrated_domain" for x in entries)}))


if __name__=="__main__":
    main()
