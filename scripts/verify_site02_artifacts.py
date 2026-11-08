"""Validate research artifacts without model inference or external downloads."""
import csv
import hashlib
import json
from pathlib import Path
import cv2
root=Path(__file__).resolve().parents[1]
checks=[]
expected={"C0001001_v10":"9926ccdd05358cab83c292d9a62f2196961de9439e97857c592a75d2993d5276","C0001011_v10":"1d9b0ff0cbf92d9d107cfb7b197fe393fea5937f1245e5bc99b852e7137c694d"}
for camera,digest in expected.items():
    path=root/"data/raw/multiview/002_site02_gaze"/(camera+".mp4")
    if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError("Input checksum mismatch: "+camera)
checks.append("both fixed input hashes")
for folder in ["site02-gpu-probe","site02-gpu-conf010","site02-gpu-conf010-imgsz960"]:
    output=root/"data/processed"/folder
    meta=json.loads((output/"run.json").read_text())
    if meta.get("missing"):raise ValueError("Incomplete camera coverage: "+folder)
    if {run["camera"] for run in meta["runs"]}!=set(expected):raise ValueError("Wrong camera set")
    for run in meta["runs"]:
        camera=run["camera"]
        with (output/(camera+"_frames.csv")).open() as f:frames=list(csv.DictReader(f))
        with (output/(camera+"_observations.csv")).open() as f:obs=list(csv.DictReader(f))
        if [int(row["frame"]) for row in frames]!=list(range(218)):raise ValueError("Frame ledger gap")
        if len(obs)!=run["observations"]:raise ValueError("Observation total mismatch")
        if sum(int(row["tracked_boxes"])==0 for row in frames)!=run["zero_track_frames"]:raise ValueError("Blank count mismatch")
        if len({row["local_id"] for row in obs})!=run["local_ids"]:raise ValueError("Local ID count mismatch")
        per_frame={i:0 for i in range(218)}
        for row in obs:
            frame=int(row["frame"])
            if frame not in per_frame:raise ValueError("Observation frame out of range")
            per_frame[frame]+=1
            if abs(float(row["relative_s"])-frame/run["fps"])>1e-6:raise ValueError("Timestamp mismatch")
        if any(per_frame[int(row["frame"])]!=int(row["tracked_boxes"]) for row in frames):raise ValueError("Per-frame ledger mismatch")
        cap=cv2.VideoCapture(str(output/(camera+"_left_tracked.mp4")));n=0
        while True:
            ok,image=cap.read()
            if not ok:break
            if image.shape[:2]!=(672,896):raise ValueError("Wrong output dimensions")
            n+=1
        cap.release()
        if n!=218:raise ValueError("Truncated output video")
    checks.append(folder+": videos, frame/observation ledgers, timestamps, IDs")
ref=root/"data/processed/site02-reference-floor/reference_floor.csv"
with ref.open() as f:rows=list(csv.DictReader(f))
if len(rows)!=218:raise ValueError("Reference coverage mismatch")
for row in rows:
    if abs(float(row["floor_x"])-(float(row["grid_x"])*.1-.75))>1e-9:raise ValueError("Reference x mismatch")
    if abs(float(row["floor_y"])-(float(row["grid_y"])*.1-2.5))>1e-9:raise ValueError("Reference y mismatch")
checks.append("reference coordinate export")
quality_dir=root/"data/processed/site02-quality"
quality_rows=[json.loads(line) for line in (quality_dir/"observations.jsonl").read_text().splitlines()]
assert len(quality_rows)==418
run_digest=hashlib.sha256((root/"data/processed/site02-gpu-conf010/run.json").read_bytes()).hexdigest()
for camera in expected:
    path=root/"data/processed/site02-gpu-conf010"/(camera+"_observations.csv")
    raw_digest=hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open() as f:raw=list(csv.DictReader(f))
    indices={};counts={}
    for row in raw:
        frame=int(row["frame"]);key=(frame,int(row["local_id"]))
        assert key not in indices
        indices[key]=counts.get(frame,0);counts[frame]=counts.get(frame,0)+1
    selected=[row for row in quality_rows if row["camera"]==camera]
    assert len(selected)==len(raw)
    for row in selected:
        assert row["source_index"]==indices[(row["frame"],row["local_id"])]
        assert row["raw_observation_artifact_sha256"]==raw_digest
        assert row["run_manifest_sha256"]==run_digest
        assert row["time_basis"]=="clip_relative"
        assert row["source_sha256"]==expected[camera]
        assert row["status"]!="strict_candidate"
        if row["status"]=="research_candidate_only":
            assert row["research_uncertain"] is True
            assert row["upstream_index"]==row["source_index"]
            assert row["upstream_track_key"]==[camera,row["local_id"]]
        else:assert row["upstream_track_key"] is None
with (quality_dir/"frames.csv").open() as f:quality_frames=list(csv.DictReader(f))
assert len(quality_frames)==436
assert sum(int(row["all_observations"]) for row in quality_frames)==418
checks.append("quality export: all source indexes, input hashes, time basis, local keys and uncertainty gates")
print(json.dumps({"status":"pass","checks":checks,"scope":"Artifact consistency only; no physical calibration or identity accuracy validation."},indent=2))
