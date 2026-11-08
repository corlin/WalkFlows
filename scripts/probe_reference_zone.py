"""Check the supplied reference path against the supplied scene entrance polygon."""
from pathlib import Path
import csv,hashlib,json
import cv2,numpy as np
import sys
from dataclasses import asdict
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from walkflows.zone_events import Sample, summarize
r=Path(__file__).resolve().parents[1];scene_path=r/"data/upstream-research/site02_scene01_v1.json";ref_path=r/"data/processed/site02-reference-floor/reference_floor.csv";out=r/"data/processed/site02-reference-zone";out.mkdir(parents=True,exist_ok=True)
scene=json.loads(scene_path.read_text());polygon=np.array(scene["entrance-zone"],dtype=np.float32)
with ref_path.open() as f:points=list(csv.DictReader(f))
rows=[];changes=[];prev=None
for p in points:
 frame=int(p["clip_frame"]);xy=(float(p["floor_x"]),float(p["floor_y"]))
 signed=cv2.pointPolygonTest(polygon,xy,True);inside=signed>=0
 rows.append({"clip_frame":frame,"relative_s":float(p["relative_s"]),"floor_x":xy[0],"floor_y":xy[1],"signed_distance_to_polygon":signed,"inside_or_boundary":inside,"source":"upstream_reference"})
 if prev is not None and inside!=prev:changes.append({"clip_frame":frame,"relative_s":float(p["relative_s"]),"transition":"entered" if inside else "exited","source":"reference_geometry_only"})
 prev=inside
if len(rows)!=218 or [x["clip_frame"] for x in rows]!=list(range(218)):raise ValueError("Reference coverage mismatch")
with (out/"frames.csv").open("w",newline="") as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
timeline=summarize([Sample(row["clip_frame"],row["relative_s"],"entrance" if row["inside_or_boundary"] else None) for row in rows],max_interval_s=0.1)
summary={"timeline_segments":[asdict(x) for x in timeline.segments],"bounded_transition_candidates":[asdict(x) for x in timeline.transitions],"observation_gaps":timeline.gaps,"maximum_accepted_interval_s":0.1,"reference_sha256":hashlib.sha256(ref_path.read_bytes()).hexdigest(),"scene_sha256":hashlib.sha256(scene_path.read_bytes()).hexdigest(),"source":"upstream_reference","zone":"upstream_entrance_zone","frame_count":len(rows),"inside_frames":sum(x["inside_or_boundary"] for x in rows),"observed_transitions":changes,"note":"Reference geometry only; no inferred customer counts, unobserved visits, physical accuracy or business events."}
(out/"summary.json").write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
