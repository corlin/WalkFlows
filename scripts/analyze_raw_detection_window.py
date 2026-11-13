"""Analyze reference-near raw detections from a recorded diagnostic probe."""
import argparse
import json
from pathlib import Path

from walkflows.multicamera_processing import file_sha256
from walkflows.raw_diagnostic import summarize_raw


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe",required=True,type=Path)
    parser.add_argument("--reference",required=True,type=Path)
    parser.add_argument("--reference-id",required=True,type=int)
    parser.add_argument("--distance",required=True,type=float)
    parser.add_argument("--high-confidence",required=True,type=float)
    parser.add_argument("--assume-aligned",required=True,action="store_true")
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    probe_hash=file_sha256(args.probe);reference_hash=file_sha256(args.reference)
    probe=json.loads(args.probe.read_text(encoding="utf-8"))
    reference=json.loads(args.reference.read_text(encoding="utf-8"))["track_results"]
    for camera in probe["project"]["cameras"]:
        if file_sha256(camera["video"]["path"])!=camera["video"]["sha256"]:
            raise ValueError("video hash mismatch")
    for model in probe["model_weights"]:
        if file_sha256(model["path"])!=model["sha256"]:raise ValueError("model hash mismatch")
    summary=summarize_raw(probe,reference,args.reference_id,args.distance,args.high_confidence)
    if file_sha256(args.probe)!=probe_hash or file_sha256(args.reference)!=reference_hash:
        raise ValueError("probe or reference changed")
    for camera in probe["project"]["cameras"]:
        if file_sha256(camera["video"]["path"])!=camera["video"]["sha256"]:
            raise ValueError("video changed during analysis")
    report={"scope":"Reference-near raw detections are spatial proximity only, not identities or recall.",
            "alignment_assumption":"Frame zero and coordinates are assumed aligned; metadata does not prove synchronization.",
            "probe_sha256":probe_hash,"reference_sha256":reference_hash,
            "script_sha256":file_sha256(__file__),"algorithm_sha256":file_sha256(Path(__file__).resolve().parents[1]/"walkflows/raw_diagnostic.py"),
            "reference_id":args.reference_id,"distance":args.distance,"probe_confidence":probe["confidence"],
            "high_confidence":args.high_confidence,"image_size":probe["image_size"],"summary":summary}
    content=json.dumps(report,indent=2,allow_nan=False)
    with args.output.open("x",encoding="utf-8") as file:file.write(content+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="near_detections"}))


if __name__=="__main__":
    main()
