"""Compare local-track zone-flow candidates with frame-indexed reference flows."""
import argparse
import csv
import json
import math
from pathlib import Path

from walkflows.generic_reference import evaluate_run
from walkflows.generic_zone_eval import flows_for_camera, nearby_flows, validate_zones
from walkflows.multicamera_processing import file_sha256
from walkflows.reference_eval import convert_reference


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",required=True,type=Path)
    parser.add_argument("--reference",required=True,type=Path)
    parser.add_argument("--zones",required=True,type=Path)
    parser.add_argument("--max-duration",required=True,type=float)
    parser.add_argument("--time-tolerance",required=True,type=float)
    parser.add_argument("--assume-aligned",action="store_true",required=True)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if (not math.isfinite(args.max_duration) or args.max_duration<=0 or
            not math.isfinite(args.time_tolerance) or args.time_tolerance<0):
        raise ValueError("invalid duration or time tolerance")
    if args.output.exists():raise FileExistsError(args.output)
    input_hashes={"run":file_sha256(args.run/"run.json"),
                  "reference":file_sha256(args.reference),"zones":file_sha256(args.zones)}
    zones=json.loads(args.zones.read_text(encoding="utf-8"))["zones"]
    if not isinstance(zones,list) or len(zones)<2:
        raise ValueError("at least two zones required")
    validate_zones(zones)
    # This also verifies input hashes, per-camera completion and metadata alignment.
    baseline=evaluate_run(args.run,args.reference,0.5)
    source=json.loads(args.reference.read_text(encoding="utf-8"))["track_results"]
    reference=convert_reference(source)
    refrows=[]
    for frame,points in reference["by_frame"].items():
        refrows.extend({"frame":frame,"id":str(p["id"]),"x":p["x"],"y":p["y"]} for p in points)
    reference_flows=flows_for_camera(refrows,zones,"reference",1/reference["frame_duration"],0,args.max_duration)
    run=json.loads((args.run/"run.json").read_text(encoding="utf-8"))
    output=[]
    for camera in run["project"]["cameras"]:
        rows=[]
        with (args.run/(camera["id"]+".csv")).open(newline="",encoding="utf-8") as file:
            for row in csv.DictReader(file):
                frame=int(row["frame"])
                if frame>=source["frames"]:continue
                def number(value):
                    try:return float(value)
                    except (TypeError,ValueError):return None
                rows.append({"frame":frame,"id":row["local_id"],"x":number(row["world_x"]),"y":number(row["world_y"])})
        flows=flows_for_camera(rows,zones,camera["id"],camera["video"]["fps"],
                               camera["offset_seconds"],args.max_duration)
        for flow in flows:
            matches=nearby_flows(flow,reference_flows,args.time_tolerance)
            flow["reference_candidates"]=[{"id":r["id"],"exit_time":r["exit_time"],
                                            "arrival_time":r["arrival_time"]} for r in matches]
        output.append({"camera":camera["id"],"flows":flows,
                       "flows_with_reference_nearby":sum(bool(f["reference_candidates"]) for f in flows)})
    if (file_sha256(args.run/"run.json")!=input_hashes["run"] or
            file_sha256(args.reference)!=input_hashes["reference"] or
            file_sha256(args.zones)!=input_hashes["zones"]):
        raise ValueError("evaluation inputs changed")
    by_id={x["id"]:x for x in run["cameras"]}
    for camera in run["project"]["cameras"]:
        if (file_sha256(args.run/(camera["id"]+".csv"))!=by_id[camera["id"]]["observations_sha256"] or
                file_sha256(camera["video"]["path"])!=camera["video"]["sha256"]):
            raise ValueError("video or observation hash changed during evaluation")
    report={"scope":"Conditional time-and-zone proximity, not identity validation, precision, recall or business events. "
                    "Reference visibility and true synchronization are unknown.",
            "alignment_assumption":baseline["alignment_assumption"],
            "max_duration_seconds":args.max_duration,"time_tolerance_seconds":args.time_tolerance,
            "zones":zones,"zones_sha256":input_hashes["zones"],"reference_sha256":input_hashes["reference"],
            "run_sha256":input_hashes["run"],"implementation_sha256":file_sha256(__file__),
            "flow_algorithm_sha256":file_sha256(Path(__file__).resolve().parents[1]/"walkflows/generic_zone_eval.py"),
            "reference_flows":reference_flows,"cameras":output}
    content=json.dumps(report,indent=2,allow_nan=False)
    with args.output.open("x",encoding="utf-8") as file:file.write(content+"\n")
    print(json.dumps({"reference_flows":len(reference_flows),"candidate_flows":sum(len(c["flows"]) for c in output),
                      "candidates_near_reference":sum(c["flows_with_reference_nearby"] for c in output)}))


if __name__=="__main__":
    main()
