"""Compare pose-first / conservative box fallback on site03 observations."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.foot_policy import select_location
from walkflows.crossview import local_duplicate_keys
floor=root/'data/processed/site03-floor-probe';pose=root/'data/processed/site03-pose-floor';tracks=root/'data/processed/site03-gpu-conf010';out=root/'data/processed/site03-hybrid-foot';out.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((floor/'summary.json').read_text());b=json.loads((pose/'summary.json').read_text());records=[];reports=[]
if a['scene_sha256']!=b['scene_sha256'] or a['native_lift_binary_sha256']!=b['native_lift_sha256']:raise ValueError('incompatible geometry provenance')
for x,y in zip(a['cameras'],b['cameras'],strict=True):
 camera=x['camera'];boxpath=floor/(camera+'_experimental_floor.csv');posepath=pose/(camera+'_pose_floor.csv');trackpath=tracks/(camera+'_observations.csv')
 if camera!=y['camera'] or sha(boxpath)!=x['projection_sha256'] or sha(posepath)!=y['output_sha256'] or sha(trackpath)!=x['source_sha256'] or x['source_sha256']!=y['track_csv_sha256']:raise ValueError('input mismatch '+camera)
 def read(path):
  with path.open() as f:return list(csv.DictReader(f))
 boxes=read(boxpath);feet=read(posepath);tracks_data=read(trackpath);key=lambda r:(int(r['frame']),int(r['local_id']))
 bm={key(r):r for r in boxes};pm={key(r):r for r in feet};tm={key(r):r for r in tracks_data}
 if len(bm)!=len(boxes) or len(pm)!=len(feet) or len(tm)!=len(tracks_data) or set(bm)!=set(pm) or set(bm)!=set(tm):raise ValueError('observation coverage mismatch')
 duplicate=local_duplicate_keys([{'frame':k[0],'id':k[1],'box':tuple(float(r[c]) for c in ('left','top','right','bottom'))} for k,r in tm.items()],containment=.9)
 current=[]
 for k,boxrow in bm.items():
  foot=pm[k];box_valid=all(int(boxrow[n])==1 for n in ('inside_calibration_hull','forward_nonparallel','in_scene_bounds'))
  box={'valid':box_valid,'x':float(boxrow['experimental_x']) if box_valid else None,'y':float(boxrow['experimental_y']) if box_valid else None}
  # The pose export includes duplicate in its own eligibility; duplicate stays a hard block.
  pose_valid=foot['research_candidate']=='1';candidate={'valid':pose_valid,'x':float(foot['floor_x']) if pose_valid else None,'y':float(foot['floor_y']) if pose_valid else None}
  result=select_location(box,candidate,duplicate=k in duplicate,max_disagreement=.75)
  row={'camera':camera,'frame':k[0],'local_id':k[1],**result,'box_geometry_valid':box_valid,'pose_geometry_candidate':pose_valid,'pose_exclusion_reasons':foot['exclusion_reasons'].split('|') if foot['exclusion_reasons'] else [],'pose_foot_kind':foot['foot_kind'] or None,'pose_pixel':[float(foot['foot_x']),float(foot['foot_y'])] if foot['foot_x'] and foot['foot_y'] else None,'strict_candidate':False}
  current.append(row);records.append(row)
 reports.append({'camera':camera,'observations':len(current),'methods':dict(Counter(r['method'] for r in current)),'strict_candidates':0})
path=out/'observations.jsonl'
with path.open('w') as f:
 for row in records:f.write(json.dumps(row,allow_nan=False)+'\n')
report={'scope':'Research-only pose-first or box fallback; no validated visibility, localization, synchronization or identity.','max_disagreement':.75,'pose_score_threshold':.5,'duplicate_containment':.9,'methods':'pose if valid; box fallback if pose absent; retain unknown if conflicting, duplicate, or neither valid','floor_summary_sha256':sha(floor/'summary.json'),'pose_summary_sha256':sha(pose/'summary.json'),'observations_sha256':sha(path),'cameras':reports}
(out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
