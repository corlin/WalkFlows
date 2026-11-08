"""Classify experimental projection domain; do not infer customer presence/identity."""
from pathlib import Path
import csv,json,collections
r=Path(__file__).resolve().parents[1];out=r/"data/processed/site02-roi-review";out.mkdir(parents=True,exist_ok=True)
summary={"scope":"Source-defined geometric domain only; not validated localization or people counting.","cameras":[]}
for cam in ["C0001001_v10","C0001011_v10"]:
    with (r/"data/processed/site02-floor-probe"/(cam+"_experimental_floor.csv")).open() as f:rows=list(csv.DictReader(f))
    counts=collections.Counter();perframe={i:collections.Counter() for i in range(218)}
    for row in rows:
        flags=[]
        if not int(row["inside_calibration_hull"]):flags.append("outside_lens_calibration_hull")
        if not int(row["forward_nonparallel"]):flags.append("invalid_ray")
        if not int(row["in_scene_bounds"]):flags.append("outside_scene_analysis_bounds")
        row["domain_status"]=";".join(flags) if flags else "candidate_in_domain"
        counts[row["domain_status"]]+=1;perframe[int(row["frame"])]["total"]+=1
        if not flags:perframe[int(row["frame"])]["candidate"]+=1
    with (out/(cam+"_domain_observations.csv")).open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    frames=[]
    for frame,c in perframe.items():
        state="no_track_output" if c["total"]==0 else "only_outside_domain_tracks" if c["candidate"]==0 else "candidate_in_domain"
        frames.append([frame,frame/15,c["total"],c["candidate"],state])
    assert sum(row[2] for row in frames)==len(rows)
    with (out/(cam+"_domain_frames.csv")).open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["frame","relative_s","all_local_track_observations","candidate_domain_observations","frame_state"]);w.writerows(frames)
    summary["cameras"].append({"camera":cam,"observation_status_counts":dict(counts),"frame_states":dict(collections.Counter(row[4] for row in frames)),"all_local_ids":len({row["local_id"] for row in rows}),"candidate_local_ids":len({row["local_id"] for row in rows if row["domain_status"]=="candidate_in_domain"})})
(out/"summary.json").write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
