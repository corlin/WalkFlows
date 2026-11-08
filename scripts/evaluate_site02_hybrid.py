"""Site02 paired baseline/hybrid comparison on identical reference-proxy support."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,hashlib,json,math,sys
import numpy as np
root=Path(__file__).resolve().parents[1];processed=root/'data/processed';quality=processed/'site02-quality/observations.jsonl';hybrid=processed/'site02-hybrid-foot';reference=processed/'site02-reference-floor/reference_floor.csv';out=processed/'site02-hybrid-eval';out.mkdir(parents=True,exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary=json.loads((hybrid/'summary.json').read_text());path=hybrid/'observations.jsonl'
if sha(path)!=summary['observations_sha256'] or sha(quality)!=summary['quality_sha256']:raise ValueError('input hash mismatch')
original=[json.loads(line) for line in quality.read_text().splitlines()];mixed=[json.loads(line) for line in path.read_text().splitlines()];key=lambda r:(r['camera'],r['frame'],r['local_id']);qm={key(r):r for r in original};hm={key(r):r for r in mixed}
if len(qm)!=len(original) or len(hm)!=len(mixed) or set(qm)!=set(hm):raise ValueError('observation key mismatch')
with reference.open() as f:refs={int(r['clip_frame']):r for r in csv.DictReader(f)}
if set(refs)!=set(range(218)):raise ValueError('reference coverage mismatch')
groups=defaultdict(list)
for k,q in qm.items():
 if q['status'] not in ('research_candidate_only','strict_candidate'):continue
 ref=refs[k[1]];dist=math.hypot(q['xy'][0]-float(ref['floor_x']),q['xy'][1]-float(ref['floor_y']));groups[(k[0],k[1])].append((k,dist))
rows=[];reports=[]
for camera in ('C0001001_v10','C0001011_v10'):
 for gate in (.5,1.):
  selected=[]
  for (cam,frame),candidates in sorted(groups.items()):
   if cam!=camera:continue
   near=[(k,d) for k,d in candidates if d<=gate]
   if len(near)!=1:continue
   k,box_error=near[0];h=hm[k]
   if h['x'] is None or h['y'] is None:continue
   ref=refs[frame];hybrid_error=math.hypot(h['x']-float(ref['floor_x']),h['y']-float(ref['floor_y']))
   row={'camera':cam,'frame':frame,'local_id':k[2],'gate':gate,'method':h['method'],'box_x':qm[k]['xy'][0],'box_y':qm[k]['xy'][1],'hybrid_x':h['x'],'hybrid_y':h['y'],'box_error':box_error,'hybrid_error':hybrid_error};selected.append(row);rows.append(row)
  delta=[x['hybrid_error']-x['box_error'] for x in selected]
  reports.append({'camera':camera,'reference_proxy_gate':gate,'paired_observations':len(selected),'methods':dict(Counter(x['method'] for x in selected)),'median_box_reference_distance':float(np.median([r['box_error'] for r in selected])) if selected else None,'median_hybrid_reference_distance':float(np.median([r['hybrid_error'] for r in selected])) if selected else None,'hybrid_closer':sum(x< -1e-9 for x in delta),'box_closer':sum(x>1e-9 for x in delta),'equal':sum(abs(x)<=1e-9 for x in delta)})
cross=[]
for gate in (.5,1.):
 byframe=defaultdict(dict)
 for row in rows:
  if row['gate']==gate:
   if row['camera'] in byframe[row['frame']]:raise ValueError('ambiguous proxy')
   byframe[row['frame']][row['camera']]=row
 support=[v for v in byframe.values() if len(v)==2];box=[];combined=[];method_pairs=Counter()
 for v in support:
  a=v['C0001001_v10'];b=v['C0001011_v10'];box.append(math.hypot(a['box_x']-b['box_x'],a['box_y']-b['box_y']));combined.append(math.hypot(a['hybrid_x']-b['hybrid_x'],a['hybrid_y']-b['hybrid_y']));method_pairs[a['method']+' / '+b['method']]+=1
 cross.append({'reference_proxy_gate':gate,'common_frames':len(support),'method_combinations':dict(method_pairs),'median_box_crossview_distance':float(np.median(box)) if box else None,'median_hybrid_crossview_distance':float(np.median(combined)) if combined else None,'box_at_most_0_5':sum(x<=.5 for x in box),'hybrid_at_most_0_5':sum(x<=.5 for x in combined)})
fields=['camera','frame','local_id','gate','method','box_x','box_y','hybrid_x','hybrid_y','box_error','hybrid_error']
with (out/'paired.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
result={'scope':'Conditional same-support reference-proximity experiment; not actual identity accuracy or customer count.','caveats':['site02 was inspected earlier; this is cross-scene, not a blinded holdout','reference association depends on baseline box distance','same frame index and reference identity are unverified assumptions','adjacent frames and tracks are correlated','fallback points are not automatically valid feet'], 'quality_sha256':sha(quality),'hybrid_sha256':sha(path),'reference_sha256':sha(reference),'paired_sha256':sha(out/'paired.csv'),'cameras':reports,'cross_camera':cross}
(out/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
