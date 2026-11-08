"""Build conservative site03 research trajectories from pose-foot candidate edges."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.journeys import build_hypotheses
pose=root/'data/processed/site03-pose-floor';proposals=root/'data/processed/site03-pose-proposals';out=root/'data/processed/site03-hypotheses';out.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((pose/'summary.json').read_text());b=json.loads((proposals/'summary.json').read_text())
if a['pose_score_threshold']!=.5 or b['score_threshold']!=.5:raise ValueError('unexpected pose threshold')
if sha(pose/'summary.json')!=b['pose_floor_summary_sha256'] or sha(proposals/'pair_candidates.csv')!=b['candidate_csv_sha256']:raise ValueError('proposal provenance mismatch')
observations=[]
for camera in a['cameras']:
 path=pose/(camera['camera']+'_pose_floor.csv')
 if sha(path)!=camera['output_sha256']:raise ValueError('pose projection mismatch')
 with path.open() as f:
  for row in csv.DictReader(f):
   if int(row['research_candidate'])==1:observations.append({'camera':camera['camera'],'id':int(row['local_id']),'frame':int(row['frame']),'x':float(row['floor_x']),'y':float(row['floor_y'])})
edges=[];evidence={}
for report in b['reports']:
 if report['threshold']!=.5:continue
 for h in report['hypotheses']:
  row={'left_camera':report['left_camera'],'left_id':h['left_id'],'right_camera':report['right_camera'],'right_id':h['right_id'],'supported':h['supported']};edges.append(row)
  evidence[(row['left_camera'],row['left_id'],row['right_camera'],row['right_id'])]={k:h[k] for k in ('frames','longest_consecutive','median_distance')}
result=build_hypotheses(observations,edges,max_spread=.5)
for edge in result['associations']:
 key=(edge['left_camera'],edge['left_id'],edge['right_camera'],edge['right_id']);edge['evidence']=evidence[key]
expected={(x['camera'],x['id'],x['frame']) for x in observations};used=[]
for hypothesis in result['hypotheses']:
 if len({m['camera'] for m in hypothesis['members']})!=len(hypothesis['members']):raise ValueError('same-camera conflict in hypothesis')
 for sample in hypothesis['samples']:
  sample['relative_s']=sample['frame']/15
  used.extend((source['camera'],source['id'],sample['frame']) for source in sample['sources'])
if len(used)!=len(expected) or set(used)!=expected:raise ValueError('observation conservation failed')
result.update({'schema_version':1,'scope':'Experimental association hypotheses only; not validated person IDs or deduplicated customer counts.','association_threshold':.5,'max_frame_spread':.5,'fps':15,'inputs':{'pose_floor_summary_sha256':sha(pose/'summary.json'),'proposal_summary_sha256':sha(proposals/'summary.json')}})
path=out/'hypotheses.json';path.write_text(json.dumps(result,indent=2,allow_nan=False))
counts=Counter(s['status'] for h in result['hypotheses'] for s in h['samples']);report={'scope':result['scope'],'hypotheses':len(result['hypotheses']),'multi_camera_hypotheses':sum(len(h['members'])>1 for h in result['hypotheses']),'local_tracks':len({(r['camera'],r['id']) for r in observations}),'input_observations':len(observations),'sample_states':dict(counts),'association_states':dict(Counter(x['status'] for x in result['associations'])),'artifact_sha256':sha(path)}
(out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
