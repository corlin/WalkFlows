"""Experimental grouping of hypotheses by candidate local tracklet links."""
from collections import defaultdict
from math import hypot,isfinite
from statistics import median
import hashlib,json

def stitch(hypotheses,links,max_spread):
 if isinstance(max_spread,bool) or not isinstance(max_spread,(int,float)) or not isfinite(max_spread) or max_spread<=0:raise ValueError('invalid spread')
 byid={h['id']:h for h in hypotheses};parent={x:x for x in byid};nodes={}
 if len(byid)!=len(hypotheses):raise ValueError('duplicate hypothesis')
 for h in hypotheses:
  for m in h['members']:
   key=(m['camera'],m['id'])
   if key in nodes:raise ValueError('duplicate member')
   nodes[key]=h['id']
 def find(a):
  while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
  return a
 for e in links:
  if e['status']!='candidate':continue
  a=nodes.get((e['camera'],e['from_id']));b=nodes.get((e['camera'],e['to_id']))
  if a is None or b is None:continue
  a,b=find(a),find(b)
  if a!=b:parent[max(a,b)]=min(a,b)
 groups=defaultdict(list)
 for ident in byid:groups[find(ident)].append(ident)
 result=[]
 for group in sorted((sorted(x) for x in groups.values())):
  frames=defaultdict(list);members=[];seen=set()
  for hid in group:
   h=byid[hid];members.extend(h['members'])
   for sample in h['samples']:
    for p in sample['sources']:
     key=(p['camera'],p['id'],sample['frame'])
     if key in seen:raise ValueError('duplicate source')
     seen.add(key);frames[sample['frame']].append(p)
  samples=[]
  for frame,points in sorted(frames.items()):
   points.sort(key=lambda p:(p['camera'],p['id']));spread=max((hypot(a['x']-b['x'],a['y']-b['y']) for i,a in enumerate(points) for b in points[i+1:]),default=0.);same_camera=len({p['camera'] for p in points})!=len(points);good=not same_camera and spread<=max_spread
   samples.append({'frame':frame,'x':median(p['x'] for p in points) if good else None,'y':median(p['y'] for p in points) if good else None,'status':'research_candidate' if good else 'spatial_conflict','reason':'same_camera_overlap' if same_camera else 'cross_view_spread' if not good else None,'sources':points})
  ident=group[0] if len(group)==1 else 'linked-'+hashlib.sha256(json.dumps(group,separators=(',',':')).encode()).hexdigest()[:16]
  result.append({'id':ident,'members':sorted(members,key=lambda m:(m['camera'],m['id'])),'input_hypotheses':group,'samples':samples})
 return result
