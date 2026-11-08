"""Compare simultaneous camera positions on the same reference-proxy support."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,itertools,json,sys
import numpy as np
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.pose_foot import compare_view_pairs
source=root/'data/processed/site03-pose-comparison';meta=json.loads((source/'summary.json').read_text());csvpath=source/'paired.csv'
if hashlib.sha256(csvpath.read_bytes()).hexdigest()!=meta['paired_sha256']:raise ValueError('paired input checksum mismatch')
groups=defaultdict(list)
with csvpath.open() as f:
 for row in csv.DictReader(f):
  for key in ('frame','reference_id'):row[key]=int(row[key])
  for key in ('box_world_x','box_world_y','foot_world_x','foot_world_y'):row[key]=float(row[key])
  groups[(float(row['confidence_threshold']),float(row['reference_gate']),row['camera'])].append(row)
out=root/'data/processed/site03-pose-crossview';out.mkdir(parents=True,exist_ok=True);reports=[];details=[]
for confidence in (.25,.5,.75):
 for gate in (.5,1.):
  cameras=sorted(cam for c,g,cam in groups if c==confidence and g==gate)
  for left,right in itertools.combinations(cameras,2):
   pairs=compare_view_pairs(groups[(confidence,gate,left)],groups[(confidence,gate,right)])
   if not pairs:continue
   box=np.array([x['box_distance'] for x in pairs]);foot=np.array([x['foot_distance'] for x in pairs]);delta=foot-box
   reports.append({'left':left,'right':right,'confidence_threshold':confidence,'reference_proxy_gate':gate,'common_support':len(pairs),'median_box_distance':float(np.median(box)),'median_foot_distance':float(np.median(foot)),'median_paired_delta':float(np.median(delta)),'box_within_0_25':int(np.sum(box<=.25)),'foot_within_0_25':int(np.sum(foot<=.25)),'box_within_0_5':int(np.sum(box<=.5)),'foot_within_0_5':int(np.sum(foot<=.5))})
   for pair in pairs:details.append({'left':left,'right':right,'confidence_threshold':confidence,'reference_proxy_gate':gate,**pair})
fields=['left','right','confidence_threshold','reference_proxy_gate','frame','reference_id','box_distance','foot_distance']
with (out/'paired_views.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(details)
report={'scope':'Conditional common-support view consistency, not identity or physical accuracy validation.','selection_bias':'Views are joined by proximity to the same reference assigned using box-based projections. Results are conditional, not independent identity ground truth; pose/box use the exact same paired keys.','input_sha256':hashlib.sha256(csvpath.read_bytes()).hexdigest(),'paired_views_sha256':hashlib.sha256((out/'paired_views.csv').read_bytes()).hexdigest(),'results':reports}
(out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
