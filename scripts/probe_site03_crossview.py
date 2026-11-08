"""Form geometry-only cross-camera candidates and compare reference proximity proxies."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,hashlib,itertools,json,statistics,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.crossview import unique_pairs,summarize_pairs,local_duplicate_keys
floor=root/'data/processed/site03-floor-probe';tracking=root/'data/processed/site03-gpu-conf010';evaluation=root/'data/processed/site03-reference-eval';out=root/'data/processed/site03-crossview';out.mkdir(parents=True,exist_ok=True)
source=json.loads((floor/'summary.json').read_text());ref_report=json.loads((evaluation/'summary.json').read_text());match_path=evaluation/'candidate_matches.csv'
if hashlib.sha256(match_path.read_bytes()).hexdigest()!=ref_report['candidate_matches_sha256']:raise ValueError('reference matches checksum mismatch')
proxies={}
with match_path.open() as f:
 for r in csv.DictReader(f):
  if float(r['threshold'])==0.5:proxies[(r['camera'],int(r['frame']),int(r['local_id']))]=r
frame_groups={};excluded={}
for entry in source['cameras']:
 if entry['status']!='complete':continue
 camera=entry['camera'];raw=tracking/(camera+'_observations.csv');projection=floor/(camera+'_experimental_floor.csv')
 if hashlib.sha256(raw.read_bytes()).hexdigest()!=entry['source_sha256'] or hashlib.sha256(projection.read_bytes()).hexdigest()!=entry['projection_sha256']:raise ValueError('input checksum mismatch')
 with raw.open() as f:boxes=list(csv.DictReader(f))
 dups=local_duplicate_keys([{'frame':int(r['frame']),'id':int(r['local_id']),'box':tuple(float(r[k]) for k in ('left','top','right','bottom'))} for r in boxes],containment=.9)
 grouped=defaultdict(list);bad=0
 with projection.open() as f:
  for r in csv.DictReader(f):
   key=(int(r['frame']),int(r['local_id']))
   if key in dups or not all(int(r[k])==1 for k in ('inside_calibration_hull','forward_nonparallel','in_scene_bounds')):bad+=1;continue
   grouped[key[0]].append({'id':key[1],'x':float(r['experimental_x']),'y':float(r['experimental_y'])})
 frame_groups[camera]=grouped;excluded[camera]={'all':len(boxes),'duplicate_flagged':len(dups),'excluded_geometry_or_duplicate':bad}
fields=['threshold','frame','left_camera','left_id','right_camera','right_id','distance','reference_proximity_proxy'];rows=[];reports=[]
for threshold in (.25,.5,1.0):
 for left,right in itertools.combinations(sorted(frame_groups),2):
  pairs=[];proxy_counts=Counter()
  for frame in sorted(frame_groups[left].keys()&frame_groups[right].keys()):
   for p in unique_pairs(frame_groups[left][frame],frame_groups[right][frame],max_distance=threshold):
    a=proxies.get((left,frame,p['left_id']));b=proxies.get((right,frame,p['right_id']))
    status='unavailable' if not a or not b else 'ambiguous' if a['multiple_reference_candidates']=='True' or b['multiple_reference_candidates']=='True' else 'same_reference_nearby' if a['reference_id']==b['reference_id'] else 'different_references_nearby'
    proxy_counts[status]+=1;pairs.append({'frame':frame,**p});rows.append({'threshold':threshold,'frame':frame,'left_camera':left,'left_id':p['left_id'],'right_camera':right,'right_id':p['right_id'],'distance':p['distance'],'reference_proximity_proxy':status})
  if pairs:
   hypotheses=summarize_pairs(pairs,min_frames=10,min_consecutive=5)
   reports.append({'threshold':threshold,'left_camera':left,'right_camera':right,'candidate_frame_pairs':len(pairs),'reference_proximity_proxy_counts':dict(proxy_counts),'hypotheses':hypotheses})
with (out/'pair_candidates.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
report={'scope':'geometry-only, camera-pair proposals, NOT global IDs or customer counts; all inputs remain research-only','rules':{'unique_within_radius_on_both_sides':True,'minimum_hypothesis_frames':10,'minimum_consecutive_frames':5,'duplicate_containment':0.9,'reference_proxy_distance':0.5},'caveats':['same frame index assumed; exposure sync unverified','foot location and physical geometry unvalidated','reference proxy is independently derived distance matching, not verified identity','unsupported views or missed detections are unknown, not no people','hypotheses are not accepted associations'], 'inputs':{'floor_summary_sha256':hashlib.sha256((floor/'summary.json').read_bytes()).hexdigest(),'reference_summary_sha256':hashlib.sha256((evaluation/'summary.json').read_bytes()).hexdigest()},'coverage':excluded,'reports':reports,'candidate_csv_sha256':hashlib.sha256((out/'pair_candidates.csv').read_bytes()).hexdigest()}
(out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
