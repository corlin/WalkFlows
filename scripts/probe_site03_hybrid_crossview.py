"""Research cross-view proposals from pose-first / box-fallback points."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,hashlib,itertools,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.crossview import unique_pairs,summarize_pairs
hybrid=root/'data/processed/site03-hybrid-foot';ref=root/'data/processed/site03-reference-eval';out=root/'data/processed/site03-hybrid-proposals';out.mkdir(parents=True,exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();meta=json.loads((hybrid/'summary.json').read_text());refmeta=json.loads((ref/'summary.json').read_text())
if sha(hybrid/'observations.jsonl')!=meta['observations_sha256'] or sha(ref/'candidate_matches.csv')!=refmeta['candidate_matches_sha256']:raise ValueError('input hash mismatch')
proxy={}
with (ref/'candidate_matches.csv').open() as f:
 for r in csv.DictReader(f):
  if float(r['threshold'])==.5:proxy[(r['camera'],int(r['frame']),int(r['local_id']))]=r
frames=defaultdict(lambda:defaultdict(list));methods={}
for line in (hybrid/'observations.jsonl').read_text().splitlines():
 r=json.loads(line);k=(r['camera'],r['frame'],r['local_id']);methods[k]=r['method']
 if r['x'] is not None:frames[r['camera']][r['frame']].append({'id':r['local_id'],'x':r['x'],'y':r['y']})
reports=[];rows=[]
for radius in (.25,.5,1.):
 for left,right in itertools.combinations(sorted(frames),2):
  pairs=[];proxies=Counter();combinations=Counter()
  for frame in sorted(frames[left].keys()&frames[right].keys()):
   for p in unique_pairs(frames[left][frame],frames[right][frame],max_distance=radius):
    ka=(left,frame,p['left_id']);kb=(right,frame,p['right_id']);a=proxy.get(ka);b=proxy.get(kb)
    status='unavailable' if not a or not b else 'ambiguous' if a['multiple_reference_candidates']=='True' or b['multiple_reference_candidates']=='True' else 'same_reference_nearby' if a['reference_id']==b['reference_id'] else 'different_references_nearby'
    combo=methods[ka]+' / '+methods[kb];combinations[combo]+=1;proxies[status]+=1;pairs.append({'frame':frame,**p});rows.append({'threshold':radius,'frame':frame,'left_camera':left,'left_id':p['left_id'],'right_camera':right,'right_id':p['right_id'],'distance':p['distance'],'reference_proximity_proxy':status,'left_method':methods[ka],'right_method':methods[kb]})
  if pairs:reports.append({'threshold':radius,'left_camera':left,'right_camera':right,'candidate_frame_pairs':len(pairs),'method_combinations':dict(combinations),'reference_proximity_proxy_counts':dict(proxies),'hypotheses':summarize_pairs(pairs,min_frames=10,min_consecutive=5)})
fields=['threshold','frame','left_camera','left_id','right_camera','right_id','distance','reference_proximity_proxy','left_method','right_method']
with (out/'pair_candidates.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
result={'scope':'Experimental hybrid proposals only; no identities, people counts or validated fusion.','hybrid_summary_sha256':sha(hybrid/'summary.json'),'reference_summary_sha256':sha(ref/'summary.json'),'candidate_csv_sha256':sha(out/'pair_candidates.csv'),'selection_bias':'Reference proximity is based on box projection, not an independent identity label.','reports':reports}
(out/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
