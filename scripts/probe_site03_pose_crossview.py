"""Pose-foot cross-camera proposals without using reference to create pairs."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,hashlib,itertools,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.crossview import unique_pairs,summarize_pairs
source=root/'data/processed/site03-pose-floor';refdir=root/'data/processed/site03-reference-eval';out=root/'data/processed/site03-pose-proposals';out.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((source/'summary.json').read_text());refmeta=json.loads((refdir/'summary.json').read_text());refpath=refdir/'candidate_matches.csv'
if sha(refpath)!=refmeta['candidate_matches_sha256']:raise ValueError('reference proxy hash mismatch')
proxies={}
with refpath.open() as f:
 for r in csv.DictReader(f):
  if float(r['threshold'])==.5:proxies[(r['camera'],int(r['frame']),int(r['local_id']))]=r
frames={}
for entry in meta['cameras']:
 camera=entry['camera'];path=source/(camera+'_pose_floor.csv')
 if sha(path)!=entry['output_sha256']:raise ValueError('pose projection mismatch '+camera)
 group=defaultdict(list)
 with path.open() as f:
  for r in csv.DictReader(f):
   if int(r['research_candidate'])==1:group[int(r['frame'])].append({'id':int(r['local_id']),'x':float(r['floor_x']),'y':float(r['floor_y'])})
 frames[camera]=group
reports=[];rows=[]
for threshold in (.25,.5,1.):
 for left,right in itertools.combinations(sorted(frames),2):
  pairs=[];proxy_count=Counter()
  for frame in sorted(frames[left].keys()&frames[right].keys()):
   for p in unique_pairs(frames[left][frame],frames[right][frame],max_distance=threshold):
    a=proxies.get((left,frame,p['left_id']));b=proxies.get((right,frame,p['right_id']))
    status='unavailable' if not a or not b else 'ambiguous' if a['multiple_reference_candidates']=='True' or b['multiple_reference_candidates']=='True' else 'same_reference_nearby' if a['reference_id']==b['reference_id'] else 'different_references_nearby'
    proxy_count[status]+=1;pairs.append({'frame':frame,**p});rows.append({'threshold':threshold,'frame':frame,'left_camera':left,'left_id':p['left_id'],'right_camera':right,'right_id':p['right_id'],'distance':p['distance'],'reference_proximity_proxy':status})
  if pairs:reports.append({'threshold':threshold,'left_camera':left,'right_camera':right,'candidate_frame_pairs':len(pairs),'reference_proximity_proxy_counts':dict(proxy_count),'hypotheses':summarize_pairs(pairs,min_frames=10,min_consecutive=5)})
fields=['threshold','frame','left_camera','left_id','right_camera','right_id','distance','reference_proximity_proxy']
with (out/'pair_candidates.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
result={'scope':'Pose-foot research candidate pairs, not global IDs, validated identity or people counts.','pair_generation':'Only pose-foot points and unique-distance gate; no reference used to construct pairs.','proxy_caveat':'Reference-nearby labels depend on box-based predicted positions and are not identity truth.','score_threshold':meta['pose_score_threshold'],'support':'10 candidate frames and 5 consecutive frames; not proof of identity','pose_floor_summary_sha256':sha(source/'summary.json'),'reference_summary_sha256':sha(refdir/'summary.json'),'candidate_csv_sha256':sha(out/'pair_candidates.csv'),'reports':reports}
(out/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
