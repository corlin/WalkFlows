"""Compare reference proxies for baseline and relaxed tracker using mutual box agreement."""
import json,csv,sys,hashlib
from pathlib import Path
from collections import defaultdict,Counter
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.association_diagnostic import diagnose
from walkflows.tracker_comparison import iou
from walkflows.reference_eval import convert_reference
p=root/'data/processed';raw=root/'data/raw/multiview/006_site03_tracks/ground-truth.json';hyp=p/'site03-hypotheses/hypotheses.json';review=p/'site03-review/data.json';experiment=p/'site03-byte095-experiment';sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
h=json.loads(hyp.read_text()); refs=convert_reference(json.loads(raw.read_text())['track_results'])['by_frame'];d=json.loads(review.read_text());obs=[]
for x in h['hypotheses']:
 for sample in x['samples']:
  for source in sample['sources']:obs.append(dict(frame=sample['frame'],**source))
m=diagnose(obs,refs,.5);lookup={(r['camera'],r['frame'],r['id']):r for r in m};reports=[]
for cam in ['C0001055_v4','C0001056_v2']:
 path=experiment/(cam+'_observations.csv');run=json.loads((experiment/(cam+'_run.json')).read_text())
 if sha(path)!=run['observations_sha256']:raise ValueError('experiment checksum mismatch')
 with path.open() as f:alt=[{k:int(v) if k in ('frame','local_id') else float(v) for k,v in r.items()} for r in csv.DictReader(f)]
 altframes=defaultdict(list);baseframes=defaultdict(list)
 for a in alt:altframes[a['frame']].append(a)
 for a in d['cameras'][cam]:baseframes[a['frame']].append(a)
 stats=defaultdict(Counter);evidence=defaultdict(list);ambiguous=0
 for r in d['cameras'][cam]:
  x=lookup.get((cam,r['frame'],r['id']))
  if not x or x['status']!='matched':continue
  box=dict(zip(('left','top','right','bottom'),r['box'])); candidates=[z for z in altframes[r['frame']] if iou(box,z)>=.8]
  if len(candidates)!=1:ambiguous+=1;continue
  v=candidates[0];competitors=[z for z in baseframes[r['frame']] if iou(dict(zip(('left','top','right','bottom'),z['box'])),v)>=.8]
  if len(competitors)!=1:ambiguous+=1;continue
  stats[v['local_id']][x['reference_id']]+=1;evidence[v['local_id']].append({'frame':r['frame'],'baseline_id':r['id'],'reference_proxy_id':x['reference_id']})
 reports.append({'camera':cam,'relaxed_track_proxy_support':[{'local_id':key,'support':dict(sorted(value.items())),'evidence':evidence[key]} for key,value in sorted(stats.items())],'excluded_nonunique_box_correspondence':ambiguous,'experiment_observations_sha256':sha(path)})
result={'scope':'Conditional reference proximity proxy transferred by mutually unique frame box overlap; not identity ground truth.','limitations':['Projection and reference completeness unvalidated.','Only baseline pose-qualified observations contribute; unmatched and nonunique observations are excluded.','Same observations are used to choose and evaluate correspondence; no independent generalization estimate.'],'reference_gate':.5,'box_iou_gate':.8,'inputs':{'reference_sha256':sha(raw),'hypotheses_sha256':sha(hyp),'review_sha256':sha(review)},'cameras':reports}
(experiment/'reference-proxy-comparison.json').write_text(json.dumps(result,indent=2));print(json.dumps([{'camera':r['camera'],'support':[{k:v for k,v in x.items() if k!='evidence'} for x in r['relaxed_track_proxy_support']]} for r in reports],indent=2))
