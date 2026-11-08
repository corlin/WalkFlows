"""Attach pose evidence for review; never change physical-quality gate decisions."""
from pathlib import Path
import csv,json,hashlib,collections
r=Path(__file__).resolve().parents[1];out=r/"data/processed/site02-pose-evidence";out.mkdir(parents=True,exist_ok=True)
quality=r/"data/processed/site02-quality/observations.jsonl"
records=[json.loads(x) for x in quality.read_text().splitlines()]
by_key={}
for camera in ["C0001001_v10","C0001011_v10"]:
 p=r/"data/processed/site02-pose-full"/(camera+"_track_pose.csv")
 with p.open() as f:
  for x in csv.DictReader(f):
   key=(camera,int(x["frame"]),int(x["local_id"]))
   if key in by_key:raise ValueError("Duplicate pose track key")
   by_key[key]=x
result=[];counts=collections.Counter();seen=set()
for record in records:
 key=(record["camera"],record["frame"],record["local_id"])
 if key in seen:raise ValueError("Duplicate quality track key")
 seen.add(key)
 if key not in by_key:raise ValueError("Missing pose track observation")
 pose=by_key[key];status=pose["match_status"]
 score=None
 if status=="unique" and pose["left_ankle_confidence"] and pose["right_ankle_confidence"]:
  score=max(float(pose["left_ankle_confidence"]),float(pose["right_ankle_confidence"]))
 indicator="unmatched_or_ambiguous" if status!="unique" else "missing_score" if score is None else "score_ge_025" if score>=.25 else "score_below_025"
 evidence={"pose_match_status":status,"max_ankle_confidence":score,"descriptive_indicator":indicator,"threshold":.25,"is_validated_visibility":False}
 result.append({"observation":record,"pose_evidence":evidence});counts[(record["camera"],record["status"],indicator)]+=1
if len(records)!=418 or len(by_key)!=418 or seen!=set(by_key):raise ValueError("Incomplete evidence join")
with (out/"observations_with_pose_evidence.jsonl").open("w") as f:
 for row in result:f.write(json.dumps(row,allow_nan=False)+"\n")
report={"export_script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"pose_input_sha256":{camera:hashlib.sha256((r/"data/processed/site02-pose-full"/(camera+"_track_pose.csv")).read_bytes()).hexdigest() for camera in ["C0001001_v10","C0001011_v10"]},"quality_input_sha256":hashlib.sha256(quality.read_bytes()).hexdigest(),"pose_summary_sha256":hashlib.sha256((r/"data/processed/site02-pose-full/summary.json").read_bytes()).hexdigest(),"scope":"Evidence-only join; quality status and reasons are unchanged. Pose confidence is not calibrated visibility or physical accuracy.","counts":[{"camera":k[0],"quality_status":k[1],"indicator":k[2],"observations":v} for k,v in sorted(counts.items())]}
(out/"summary.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
