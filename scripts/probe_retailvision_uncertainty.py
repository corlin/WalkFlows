"""Run pinned upstream fusion on experimental candidates; no accepted global identities."""
from pathlib import Path
import csv,json,collections,importlib.util,sys,statistics,math,hashlib
r=Path(__file__).resolve().parents[1];source=r/"data/upstream-research/retailvision-fusion.py"
spec=importlib.util.spec_from_file_location("research_retailvision_fusion",source);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
out=r/"data/processed/retailvision-uncertainty-probe";out.mkdir(parents=True,exist_ok=True)
cameras=["C0001001_v10","C0001011_v10"];groups=[]
for cam in cameras:
    with (r/"data/processed/site02-gpu-conf010"/(cam+"_observations.csv")).open() as f:confidence={(int(x["frame"]),int(x["local_id"])):float(x["confidence"]) for x in csv.DictReader(f)}
    grouped=collections.defaultdict(list)
    with (r/"data/processed/site02-roi-review"/(cam+"_domain_observations.csv")).open() as f:
        for x in csv.DictReader(f):
            if x["domain_status"]!="candidate_in_domain":continue
            frame=int(x["frame"]);tid=int(x["local_id"]);grouped[frame].append({"frame":frame,"id":tid,"xy":(float(x["experimental_x"]),float(x["experimental_y"])),"confidence":confidence[(frame,tid)]})
    groups.append(grouped)
with (r/"data/processed/site02-reference-floor/reference_floor.csv").open() as f:ref={int(x["clip_frame"]):(float(x["floor_x"]),float(x["floor_y"])) for x in csv.DictReader(f)}
frames=[f for f in range(218) if len(groups[0][f])==len(groups[1][f])==1];reports=[];ledger=[]
for radius in [.25,.50,.75]:
 for mark_uncertain in [False,True]:
    fused=[];merged=[];conditional=[];baseline=[];conf=[]
    for frame in frames:
        observations=[]
        for i in range(2):
            item=groups[i][frame][0];observations.append(module.Observation(camera_id=cameras[i],index=0,xy=item["xy"],confidence=item["confidence"],uncertain=(i==1 and mark_uncertain),track_key=(cameras[i],item["id"])))
        detections=module.fuse_views(observations,radius_m=radius);fused.extend(detections)
        for detection in detections:
            ledger.append({"frame":frame,"radius_m":radius,"camera2_assumed_uncertain":mark_uncertain,"experimental_x":detection.xy[0],"experimental_y":detection.xy[1],"upstream_confidence":detection.confidence,"support_cameras":";".join(o.camera_id for o in detection.observations),"support_local_ids":";".join(str(o.track_key) for o in detection.observations),"uncertain_supports":sum(o.uncertain for o in detection.observations),"provenance":"hypothesis_only_no_global_id"})
        for detection in detections:
            if len(detection.observations)==2:
                merged.append(frame);conditional.append(math.dist(detection.xy,ref[frame]));baseline.append(math.dist(observations[0].xy,ref[frame]));conf.append(detection.confidence)
                if mark_uncertain and math.dist(detection.xy,observations[0].xy)>1e-10:raise AssertionError("Uncertain camera moved certain anchor")
    reports.append({"radius_m":radius,"camera2_assumed_uncertain":mark_uncertain,"input_frames":len(frames),"two_camera_group_frames":len(merged),"output_groups":len(fused),"median_conditional_reference_distance_m":statistics.median(conditional) if conditional else None,"same_support_camera1_reference_distance_m":statistics.median(baseline) if baseline else None,"median_fused_confidence":statistics.median(conf) if conf else None})
result={"upstream_commit":"a0fae89b97fa45dd7e86ac0627935a682ec68ce8","source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"scope":"Camera2-uncertain is an explicit experimental assumption from occlusion review; camera1 is not proven accurate. Reference correspondence and synchronization unvalidated. Group counts are not customer counts, conditional distances are not accepted accuracy metrics.","reports":reports}
with (out/"experimental_groups.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(ledger[0]));w.writeheader();w.writerows(ledger)
(out/"summary.json").write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
