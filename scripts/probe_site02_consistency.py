"""Explore source-aligned floor candidate distances; no automatic offset/identity selection."""
from pathlib import Path
import csv,json,collections,sys,statistics
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r))
from walkflows.candidates import candidates_at_frame
out=r/"data/processed/site02-consistency";out.mkdir(parents=True,exist_ok=True)
def load(camera):
    groups=collections.defaultdict(list)
    with (r/"data/processed/site02-roi-review"/(camera+"_domain_observations.csv")).open() as f:
        for row in csv.DictReader(f):
            if row["domain_status"]!="candidate_in_domain":continue
            frame=int(row["frame"]);groups[frame].append({"frame":frame,"local_id":int(row["local_id"]),"world_x":float(row["experimental_x"]),"world_y":float(row["experimental_y"])})
    return groups
left=load("C0001001_v10");right=load("C0001011_v10");reports=[];baseline=[]
for offset in range(-5,6):
    pairs=[];ambiguous=0;common=0
    for frame in range(218):
        a=left.get(frame,[]);b=right.get(frame+offset,[])
        if not a or not b:continue
        common+=1
        if len(a)!=1 or len(b)!=1:ambiguous+=1;continue
        adjusted=[dict(b[0],frame=frame)]
        for candidate in candidates_at_frame(a,adjusted,float("inf")):
            candidate["right_frame"]=frame+offset;pairs.append(candidate)
    distances=[p["distance"] for p in pairs]
    report={"right_frame_offset":offset,"common_observed_frames":common,"excluded_multiple_candidate_frames":ambiguous,"single_candidate_pairs":len(pairs),"median_distance_m":statistics.median(distances) if distances else None,"pairs_within_025m":sum(d<=.25 for d in distances),"pairs_within_050m":sum(d<=.50 for d in distances),"pairs_within_100m":sum(d<=1 for d in distances)}
    reports.append(report)
    if offset==0:baseline=pairs
with (out/"same_index_pairs.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["frame","left_id","right_id","distance","right_frame"]);w.writeheader();w.writerows(baseline)
summary={"assumptions":"Experimental projected points; index offset sweep is sensitivity only. Neither synchronization nor same-person identity is established. Multiple in-domain candidates are excluded, not resolved by nearest-neighbor assignment.","offset_definition":"right_frame = left_frame + offset; 15fps; sweep +-5 frames","do_not_select_offset_automatically":True,"sweep":reports}
fixed_frames=[frame for frame in range(218) if len(left.get(frame,[]))==1 and all(len(right.get(frame+offset,[]))==1 for offset in range(-5,6))]
fixed_sweep=[]
for offset in range(-5,6):
    distances=[]
    for frame in fixed_frames:
        pair=candidates_at_frame(left[frame],[dict(right[frame+offset][0],frame=frame)],float("inf"))[0]
        distances.append(pair["distance"])
    fixed_sweep.append({"offset":offset,"pairs":len(distances),"median_distance_m":statistics.median(distances) if distances else None})
summary["fixed_support_frames"]=fixed_frames
summary["fixed_support_sweep"]=fixed_sweep
vectors=[]
for pair in baseline:
    frame=pair["frame"];a=left[frame][0];b=right[frame][0]
    vectors.append([b["world_x"]-a["world_x"],b["world_y"]-a["world_y"]])
summary["same_index_median_signed_difference_m"]=[statistics.median(v[i] for v in vectors) for i in range(2)]
(out/"summary.json").write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
