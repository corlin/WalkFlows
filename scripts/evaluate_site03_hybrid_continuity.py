"""Evaluate pose-first/box-fallback observations under fixed pose-only associations."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.hybrid_journeys import augment_hypotheses
from walkflows.association_diagnostic import diagnose
from walkflows.reference_eval import convert_reference
p=root/'data/processed';hpath=p/'site03-hypotheses/hypotheses.json';hs=p/'site03-hypotheses/summary.json';source=p/'site03-hybrid-foot/observations.jsonl';ss=p/'site03-hybrid-foot/summary.json';ref=root/'data/raw/multiview/006_site03_tracks/ground-truth.json';out=p/'site03-hybrid-continuity';out.mkdir(parents=True,exist_ok=True);sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
h=json.loads(hpath.read_text());hsummary=json.loads(hs.read_text());meta=json.loads(ss.read_text())
if sha(hpath)!=hsummary['artifact_sha256'] or sha(source)!=meta['observations_sha256']:raise ValueError('input hash mismatch')
rows=[json.loads(x) for x in source.read_text().splitlines()];expanded=augment_hypotheses(h['hypotheses'],rows,h['max_frame_spread']);degraded=augment_hypotheses(h['hypotheses'],rows,h['max_frame_spread'],prefer_pose_on_mixed_conflict=True)
refs=convert_reference(json.loads(ref.read_text())['track_results'])['by_frame'];sample_rows=[]
for hypothesis in expanded:
 for sample in hypothesis['samples']:
  for point in sample['sources']:sample_rows.append(dict(camera=point['camera'],id=point['id'],frame=sample['frame'],x=point['x'],y=point['y'],method=point['method']))
member_keys={(m['camera'],m['id']) for h0 in h['hypotheses'] for m in h0['members']}
expected={(r['camera'],r['local_id'],r['frame']) for r in rows if (r['camera'],r['local_id']) in member_keys and r['x'] is not None and r['y'] is not None}
actual=[(r['camera'],r['id'],r['frame']) for r in sample_rows]
if len(actual)!=len(expected) or set(actual)!=expected:raise ValueError('alternate observations not conserved')
comparison=diagnose(sample_rows,refs,.5);by_method=defaultdict(Counter)
for r in comparison:by_method[r['method']][r['status']]+=1

def metrics(hypotheses):
 valid=conflicts=adjacent=gaps=0
 for h in hypotheses:
  previous=None
  for s in h['samples']:
   if s['status']!='research_candidate':conflicts+=1;previous=None;continue
   valid+=1
   if previous is not None:
    if s['frame']==previous+1:adjacent+=1
    else:gaps+=1
   previous=s['frame']
 return {'hypotheses':len(hypotheses),'valid_samples':valid,'spatial_conflicts':conflicts,'adjacent_valid_frame_pairs':adjacent,'between_valid_gaps':gaps}
artifact=out/'hypotheses.json';artifact.write_text(json.dumps({'scope':'Experimental same fixed association groups with alternate per-source position; not validated identities or customer counts.','hypotheses':expanded},indent=2,allow_nan=False))
degraded_path=out/'hypotheses-pose-priority.json';degraded_path.write_text(json.dumps({'scope':'Experimental pose priority on mixed source conflict; discarded source retained, not validated identities.','hypotheses':degraded},indent=2,allow_nan=False))
report={'scope':'Exploratory fixed-membership comparison; reference proximity is not independent identity or localization truth.','association_policy':'Pose-derived membership unchanged; no new cross-camera edges.','pose':metrics(h['hypotheses']),'hybrid':metrics(expanded),'hybrid_pose_priority':{**metrics(degraded),'degraded_mixed_conflicts':sum(s.get('degraded_reason')=='mixed_source_conflict' for h0 in degraded for s in h0['samples'])},'pose_priority_artifact_sha256':sha(degraded_path),'source_methods':dict(Counter(r['method'] for r in sample_rows)),'reference_gate':.5,'reference_proxy_by_method':{k:dict(v) for k,v in sorted(by_method.items())},'inputs':{'hypotheses_sha256':sha(hpath),'hybrid_observations_sha256':sha(source),'reference_sha256':sha(ref)},'artifact_sha256':sha(artifact)}
(out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
