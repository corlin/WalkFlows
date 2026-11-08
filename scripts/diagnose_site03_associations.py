"""Compare research hypothesis sources with reference proximity, with ambiguity retained."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.association_diagnostic import diagnose
from walkflows.reference_eval import convert_reference
raw=root/'data/raw/multiview/006_site03_tracks/ground-truth.json'
hyp=root/'data/processed/site03-hypotheses/hypotheses.json'
out=root/'data/processed/site03-association-diagnostic';out.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reference=convert_reference(json.loads(raw.read_text())['track_results'])['by_frame']
data=json.loads(hyp.read_text()); observations=[]
for h in data['hypotheses']:
 for sample in h['samples']:
  for source in sample['sources']:
   observations.append(dict(hypothesis=h['id'],frame=sample['frame'],camera=source['camera'],id=source['id'],x=source['x'],y=source['y']))
results=[]
for radius in (.25,.5,1.):
 rows=diagnose(observations,reference,radius);counts=Counter(r['status'] for r in rows); by_hyp=defaultdict(Counter); by_member=defaultdict(Counter); by_ref_frame=defaultdict(set)
 for r in rows:
  if r['status']=='matched':
   by_hyp[r['hypothesis']][r['reference_id']]+=1
   by_member[(r['hypothesis'],r['camera'],r['id'])][r['reference_id']]+=1
   by_ref_frame[(r['reference_id'],r['frame'])].add(r['hypothesis'])
 results.append({'radius':radius,'status_counts':dict(counts),'hypotheses':[{'id':h['id'],'members':h['members'],'reference_proxy_support':dict(sorted(by_hyp[h['id']].items())),'member_proxy_support':[dict(camera=m['camera'],id=m['id'],reference_proxy_support=dict(sorted(by_member[(h['id'],m['camera'],m['id'])].items()))) for m in h['members']]} for h in data['hypotheses']],'same_reference_multiple_hypothesis_frames':sum(len(v)>1 for v in by_ref_frame.values()),'same_reference_multiple_hypothesis_examples':[{'reference_id':key[0],'frame':key[1],'hypotheses':sorted(value)} for key,value in sorted(by_ref_frame.items()) if len(value)>1]})
report={'scope':'Reference proximity proxy only; not identity accuracy, false-merge rate, false-split rate, or customer counts.','limitations':['No per-camera visibility truth; reference completeness and projection accuracy unvalidated.','Spatial assignment is conditional on radius and projection, and uses the same geometry as association.','Multiple proxy IDs within a hypothesis or simultaneous duplicate hypotheses are investigation candidates, not proven mistakes.'],'inputs':{'reference_sha256':sha(raw),'hypotheses_sha256':sha(hyp)},'observations':len(observations),'results':results}
(out/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False));print(json.dumps(report,indent=2))
