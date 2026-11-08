"""Export all experimental observations with explicit evidence and strict/research gates."""
from pathlib import Path
from dataclasses import asdict
import csv,json,collections,hashlib,importlib.util,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.quality import Observation,Quality,adapt
source=root/"data/upstream-research/retailvision-fusion.py"
source_digest=hashlib.sha256(source.read_bytes()).hexdigest()
if source_digest!="93216d5c55705322de86b5b707a60239205f9ea7fa58ee0dcb9d31132b914fa3":raise ValueError("Pinned upstream source checksum mismatch")
spec=importlib.util.spec_from_file_location("quality_retailvision",source);upstream=importlib.util.module_from_spec(spec);sys.modules[spec.name]=upstream;spec.loader.exec_module(upstream)
out=root/"data/processed/site02-quality";out.mkdir(parents=True,exist_ok=True)
run=json.loads((root/"data/processed/site02-gpu-conf010/run.json").read_text());video_sources={r["camera"]:r for r in run["runs"]}
run_manifest_digest=hashlib.sha256((root/"data/processed/site02-gpu-conf010/run.json").read_bytes()).hexdigest()
records=[];ledger=[];summary=[]
for camera in ["C0001001_v10","C0001011_v10"]:
    with (root/"data/processed/site02-gpu-conf010"/(camera+"_observations.csv")).open() as f:raw=list(csv.DictReader(f))
    groups=collections.defaultdict(list)
    for row in raw:groups[int(row["frame"])].append(row)
    duplicate=set()
    for frame,group in groups.items():
        for i,a in enumerate(group):
            for b in group[i+1:]:
                A=[float(a[k]) for k in ["left","top","right","bottom"]];B=[float(b[k]) for k in ["left","top","right","bottom"]]
                inter=max(0,min(A[2],B[2])-max(A[0],B[0]))*max(0,min(A[3],B[3])-max(A[1],B[1]));area=min((A[2]-A[0])*(A[3]-A[1]),(B[2]-B[0])*(B[3]-B[1]))
                if area>0 and inter/area>=.9:duplicate.update([(frame,int(a["local_id"])),(frame,int(b["local_id"]))])
    confidences={(int(row["frame"]),int(row["local_id"])):float(row["confidence"]) for row in raw}
    if len(confidences)!=len(raw):raise ValueError("Duplicate local keys within camera/frame")
    raw_digest=hashlib.sha256((root/"data/processed/site02-gpu-conf010"/(camera+"_observations.csv")).read_bytes()).hexdigest()
    with (root/"data/processed/site02-floor-probe"/(camera+"_experimental_floor.csv")).open() as f:floor=list(csv.DictReader(f))
    counts=collections.Counter();reason_counts=collections.Counter();perframe=collections.defaultdict(collections.Counter)
    projection_digest=hashlib.sha256((root/"data/processed/site02-floor-probe"/(camera+"_experimental_floor.csv")).read_bytes()).hexdigest()
    for row in floor:
        index=sum(perframe[int(row["frame"])].values())
        frame=int(row["frame"]);tid=int(row["local_id"])
        q=Quality(inside_hull=bool(int(row["inside_calibration_hull"])),in_scene=bool(int(row["in_scene_bounds"])),forward_ray=bool(int(row["forward_nonparallel"])),duplicate_candidate=(frame,tid) in duplicate)
        observation=Observation(camera=camera,frame=frame,local_id=tid,fps=video_sources[camera]["fps"],confidence=confidences[(frame,tid)],xy=(float(row["experimental_x"]),float(row["experimental_y"])),source_sha256=video_sources[camera]["sha256"],projection_version="experimental-site02-floor-v1",quality=q)
        strict,reasons=adapt(observation,upstream.Observation,index=index)
        research,_=adapt(observation,upstream.Observation,research=True,index=index)
        if strict is not None:status="strict_candidate"
        elif research is not None:status="research_candidate_only";assert research.uncertain
        else:status="hard_excluded"
        record=asdict(observation);record.update(schema_version=1,source_index=index,raw_observation_artifact_sha256=raw_digest,run_manifest_sha256=run_manifest_digest,time_basis="clip_relative",projection_artifact_sha256=projection_digest,upstream_index=research.index if research is not None else None,timestamp_s=observation.timestamp_s,status=status,reasons=list(reasons),research_uncertain=research.uncertain if research is not None else None,identity_scope="camera_local",upstream_track_key=list(research.track_key) if research is not None else None)
        records.append(record);counts[status]+=1;reason_counts.update(reasons);perframe[frame][status]+=1
    for frame in range(218):
        c=perframe[frame];total=sum(c.values());state="no_track_output" if not total else "strict_candidate" if c["strict_candidate"] else "research_candidate_only" if c["research_candidate_only"] else "hard_excluded_only"
        ledger.append({"camera":camera,"frame":frame,"relative_s":frame/video_sources[camera]["fps"],"all_observations":total,"strict_candidates":c["strict_candidate"],"research_candidates":c["research_candidate_only"],"hard_excluded":c["hard_excluded"],"frame_state":state})
    assert sum(counts.values())==len(raw)==len(floor)
    summary.append({"camera":camera,"observations":len(floor),"statuses":dict(counts),"reason_counts":dict(reason_counts)})
with (out/"observations.jsonl").open("w") as f:
    for record in records:f.write(json.dumps(record,allow_nan=False)+"\n")
with (out/"frames.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(ledger[0]));w.writeheader();w.writerows(ledger)
assert len(records)==418 and len(ledger)==436
assert all(record["status"]!="strict_candidate" for record in records)
report={"schema_version":1,"upstream_source_sha256":source_digest,"exporter_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"quality_module_sha256":hashlib.sha256((root/"walkflows/quality.py").read_bytes()).hexdigest(),"scope":"Explicit provenance/quality adaptation only; zero strict candidates means insufficient verified evidence, not zero people.","foot_visibility_policy":"unknown for all observations; no per-frame foot labels inferred from sparse visual inspection","duplicate_policy":"same-frame containment >=0.9 is a review heuristic; flagged rows preserved but not passed to upstream","cameras":summary}
(out/"summary.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
