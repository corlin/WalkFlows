"""Frame coverage report; counts observations, never customers."""
from pathlib import Path
import csv,json,collections,hashlib
r=Path(__file__).resolve().parents[1];quality=r/"data/processed/site02-quality/frames.csv";evidence=r/"data/processed/site02-pose-evidence/observations_with_pose_evidence.jsonl";out=r/"data/processed/site02-coverage";out.mkdir(parents=True,exist_ok=True)
with quality.open() as f:frames=list(csv.DictReader(f))
records=[json.loads(line) for line in evidence.read_text().splitlines()]
groups=collections.defaultdict(collections.Counter)
for item in records:
 o=item["observation"];e=item["pose_evidence"]
 groups[(o["camera"],o["frame"])][e["descriptive_indicator"]]+=1
rows=[];summary=[]
for row in frames:
 key=(row["camera"],int(row["frame"]));counts=groups.get(key,collections.Counter());n=sum(counts.values())
 if n!=int(row["all_observations"]):raise ValueError("Frame/evidence observation mismatch")
 rows.append({**row,"pose_score_ge_025":counts["score_ge_025"],"pose_score_below_025":counts["score_below_025"],"pose_unmatched_or_ambiguous":counts["unmatched_or_ambiguous"],"pose_missing_score":counts["missing_score"]})
for camera in sorted({row["camera"] for row in rows}):
 camera_rows=[row for row in rows if row["camera"]==camera]
 if [int(row["frame"]) for row in camera_rows]!=list(range(218)):raise ValueError("Missing or reordered frame")
 summary.append({"camera":camera,"frames":len(camera_rows),"frame_states":dict(collections.Counter(row["frame_state"] for row in camera_rows)),"observation_count":sum(int(row["all_observations"]) for row in camera_rows)})
if len(rows)!=436 or len(records)!=418:raise ValueError("Unexpected coverage")
with (out/"frame_coverage.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
result={"scope":"Observation and output coverage only; no-track is unknown, not zero people. Pose scores are not validated visibility.","quality_frames_sha256":hashlib.sha256(quality.read_bytes()).hexdigest(),"pose_evidence_sha256":hashlib.sha256(evidence.read_bytes()).hexdigest(),"cameras":summary}
(out/"summary.json").write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
