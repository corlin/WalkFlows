"""Build a mixed direct-pose research variant and compare scene coverage."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,itertools,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));sys.path.insert(0,str(root/'scripts'))
from fetch_site03_sample import FILES,valid
from walkflows.artifact_cache import sha256
from walkflows.crossview import unique_pairs,summarize_pairs,local_duplicate_keys
from walkflows.journeys import build_hypotheses
from walkflows.reference_eval import convert_reference
from walkflows.scene_reference_coverage import compare_scene
p=root/'data/processed';baseline=p/'site03-pose-floor';meta=json.loads((baseline/'summary.json').read_text());cameras=[x['camera'] for x in meta['cameras']];targets={'C0001055_v4','C0001056_v2'}
observations=[];inputs={}
for cam in cameras:
 if cam in targets:
  d=p/'site03-direct-pose-probe'/cam;path=d/'observations.csv';report=json.loads((d/'report.json').read_text())
  if sha256(path)!=report['observations_sha256'] or report['camera']!=cam or report['scene_sha256']!=meta['scene_sha256'] or report['script_sha256']!=sha256(root/'scripts/probe_site03_pose_direct.py'): raise ValueError('direct input mismatch')
  with path.open() as f: rows=list(csv.DictReader(f))
  duplicates=local_duplicate_keys([{'frame':int(x['frame']),'id':int(x['local_id']),'box':tuple(float(x[k]) for k in ('left','top','right','bottom'))} for x in rows],containment=.9)
  chosen=[x for x in rows if int(x['geometry_valid'])==1 and (int(x['frame']),int(x['local_id'])) not in duplicates]
  inputs[cam]={'kind':'direct_pose','observations_sha256':sha256(path),'report_sha256':sha256(d/'report.json')}
 else:
  path=baseline/(cam+'_pose_floor.csv');entry=next(x for x in meta['cameras'] if x['camera']==cam)
  if sha256(path)!=entry['output_sha256']:raise ValueError('baseline input mismatch')
  with path.open() as f: rows=list(csv.DictReader(f))
  chosen=[x for x in rows if int(x['research_candidate'])==1]
  inputs[cam]={'kind':'baseline','observations_sha256':sha256(path)}
 for x in chosen:observations.append({'camera':cam,'id':int(x['local_id']),'frame':int(x['frame']),'x':float(x['floor_x']),'y':float(x['floor_y'])})
frames={cam:defaultdict(list) for cam in cameras}
for x in observations:frames[x['camera']][x['frame']].append({'id':x['id'],'x':x['x'],'y':x['y']})
edges=[];pair_evidence=[]
for left,right in itertools.combinations(sorted(cameras),2):
 pairs=[]
 for frame in sorted(frames[left].keys()&frames[right].keys()):
  pairs.extend({'frame':frame,**v} for v in unique_pairs(frames[left][frame],frames[right][frame],max_distance=.5))
 for item in summarize_pairs(pairs,min_frames=10,min_consecutive=5):
  edges.append({'left_camera':left,'left_id':item['left_id'],'right_camera':right,'right_id':item['right_id'],'supported':item['supported']});pair_evidence.append({'left_camera':left,'right_camera':right,**item})
result=build_hypotheses(observations,edges,max_spread=.5)
used=[(s['camera'],s['id'],sample['frame']) for h in result['hypotheses'] for sample in h['samples'] for s in sample['sources']]
expected={(o['camera'],o['id'],o['frame']) for o in observations}
if len(used)!=len(expected) or set(used)!=expected:raise ValueError('observation conservation failure')
for h in result['hypotheses']:
 for s in h['samples']:s['relative_s']=s['frame']/15
result.update({'scope':'experimental mixed direct-pose research hypotheses; not validated identities','inputs':inputs,'fps':15})
out=p/'site03-direct-pose-journeys';out.mkdir(parents=True,exist_ok=True);path=out/'hypotheses.json';path.write_text(json.dumps(result,indent=2,allow_nan=False))
raw=root/'data/raw/multiview/006_site03_tracks/ground-truth.json'
if not valid(raw,FILES['ground-truth.json']):raise ValueError('reference checksum mismatch')
ref=convert_reference(json.loads(raw.read_text())['track_results'])['by_frame']
coverage=compare_scene(result['hypotheses'],ref,400,.5);base=p/'site03-hypotheses/hypotheses.json';base_meta=json.loads((base.parent/'summary.json').read_text())
if sha256(base)!=base_meta['artifact_sha256']:raise ValueError('baseline hypothesis checksum mismatch')
base_coverage=compare_scene(json.loads(base.read_text())['hypotheses'],ref,400,.5)
counts=lambda c:{k:v for k,v in c.items() if k!='frames'}
report={'script_sha256':sha256(Path(__file__)),'scope':'exploratory same-sample mixed model, no identity, accuracy or customer-count validation','inputs':inputs,'reference_sha256':sha256(raw),'baseline_hypotheses_sha256':sha256(base),'hypotheses_sha256':sha256(path),'input_observations':len(observations),'hypotheses':len(result['hypotheses']),'multi_camera_hypotheses':sum(len(h['members'])>1 for h in result['hypotheses']),'sample_states':dict(Counter(s['status'] for h in result['hypotheses'] for s in h['samples'])),'association_states':dict(Counter(a['status'] for a in result['associations'])),'pairs':pair_evidence,'reference_radius':.5,'baseline_coverage':counts(base_coverage),'direct_mixed_coverage':counts(coverage)}
(out/'report.json').write_text(json.dumps(report,indent=2));(out/'coverage.json').write_text(json.dumps(coverage,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('pairs','inputs')},indent=2))
