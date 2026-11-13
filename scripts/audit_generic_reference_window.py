"""Audit reference-near projected observations in a fixed frame window."""
import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

from walkflows.generic_reference import evaluate_run
from walkflows.multicamera_processing import file_sha256
from walkflows.reference_eval import convert_reference


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",required=True,type=Path)
    parser.add_argument("--reference",required=True,type=Path)
    parser.add_argument("--reference-id",required=True,type=int)
    parser.add_argument("--first-frame",required=True,type=int)
    parser.add_argument("--last-frame",required=True,type=int)
    parser.add_argument("--distance",required=True,type=float)
    parser.add_argument("--assume-aligned",required=True,action="store_true")
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.first_frame<0 or args.last_frame<args.first_frame or args.output.exists():
        raise ValueError("invalid frame window or output exists")
    baseline=evaluate_run(args.run,args.reference,args.distance)
    source=json.loads(args.reference.read_text(encoding="utf-8"))["track_results"]
    reference=convert_reference(source)
    if args.last_frame>=source["frames"]:raise ValueError("frame window outside reference")
    targets={}
    for frame in range(args.first_frame,args.last_frame+1):
        found=[p for p in reference["by_frame"][frame] if p["id"]==args.reference_id]
        if found:targets[frame]=found[0]
    if not targets:raise ValueError("reference ID absent in selected window")
    run=json.loads((args.run/"run.json").read_text(encoding="utf-8"))
    reports=[]
    for camera in run["project"]["cameras"]:
        near=[]
        with (args.run/(camera["id"]+".csv")).open(newline="",encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                frame=int(row["frame"])
                if frame not in targets or not row["world_x"] or not row["world_y"]:continue
                x,y=float(row["world_x"]),float(row["world_y"])
                if not math.isfinite(x) or not math.isfinite(y):continue
                target=targets[frame]
                distance=math.hypot(x-target["x"],y-target["y"])
                if distance<=args.distance:
                    near.append({"frame":frame,"local_id":row["local_id"] or None,"distance":distance})
        counts=Counter(x["frame"] for x in near)
        reports.append({"camera":camera["id"],"near_rows":len(near),
                        "near_rows_with_local_id":sum(x["local_id"] is not None for x in near),
                        "near_frames":len(counts),"rows":near})
    if file_sha256(args.run/"run.json")!=baseline["run_sha256"] or file_sha256(args.reference)!=baseline["reference_sha256"]:
        raise ValueError("input changed during audit")
    by_id={x["id"]:x for x in run["cameras"]}
    for camera in run["project"]["cameras"]:
        if (file_sha256(args.run/(camera["id"]+".csv"))!=by_id[camera["id"]]["observations_sha256"] or
                file_sha256(camera["video"]["path"])!=camera["video"]["sha256"]):
            raise ValueError("video or observations changed during audit")
    report={"scope":"Reference proximity is a conditional diagnostic, not identity or visibility evidence.",
            "reference_id":args.reference_id,"first_frame":args.first_frame,"last_frame":args.last_frame,
            "reference_present_frames":len(targets),"distance":args.distance,
            "alignment_assumption":baseline["alignment_assumption"],"run_sha256":baseline["run_sha256"],
            "reference_sha256":baseline["reference_sha256"],"script_sha256":file_sha256(__file__),
            "cameras":reports}
    content=json.dumps(report,indent=2,allow_nan=False)
    with args.output.open("x",encoding="utf-8") as file:file.write(content+"\n")
    print(json.dumps({"reference_present_frames":len(targets),
                      "near_rows":sum(x["near_rows"] for x in reports),
                      "near_rows_with_local_id":sum(x["near_rows_with_local_id"] for x in reports)}))


if __name__=="__main__":
    main()
