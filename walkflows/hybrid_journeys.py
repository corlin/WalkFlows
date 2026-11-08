"""Compare alternate coordinates within fixed research association hypotheses."""
from collections import defaultdict
from math import hypot,isfinite
from statistics import median

def augment_hypotheses(hypotheses,observations,max_spread,*,prefer_pose_on_mixed_conflict=False):
 if type(prefer_pose_on_mixed_conflict) is not bool:raise ValueError('invalid conflict policy')
 if isinstance(max_spread,bool) or not isinstance(max_spread,(int,float)) or not isfinite(max_spread) or max_spread<=0:raise ValueError('invalid spread')
 members={};ids=set()
 for h in hypotheses:
  if not isinstance(h.get('id'),str) or not h['id'] or h['id'] in ids:raise ValueError('invalid hypothesis')
  ids.add(h['id']);cams=set()
  for m in h['members']:
   key=(m['camera'],m['id'])
   if key in members or m['camera'] in cams:raise ValueError('duplicate member')
   members[key]=h['id'];cams.add(m['camera'])
 grouped=defaultdict(lambda:defaultdict(list));seen=set()
 for r in observations:
  camera,ident,frame=r['camera'],r['local_id'],r['frame'];key=(camera,ident,frame)
  if key in seen or not isinstance(camera,str) or type(ident) is not int or type(frame) is not int or frame<0:raise ValueError('invalid observation key')
  seen.add(key);x,y=r['x'],r['y']
  if x is None and y is None:continue
  if isinstance(x,bool) or isinstance(y,bool) or not isinstance(x,(int,float)) or not isinstance(y,(int,float)) or not isfinite(x) or not isfinite(y):raise ValueError('invalid position')
  if (camera,ident) in members:grouped[members[(camera,ident)]][frame].append({'camera':camera,'id':ident,'x':x,'y':y,'method':r['method']})
 result=[]
 for h in hypotheses:
  samples=[]
  for frame,points in sorted(grouped[h['id']].items()):
   points.sort(key=lambda p:(p['camera'],p['id']));spread=max((hypot(a['x']-b['x'],a['y']-b['y']) for i,a in enumerate(points) for b in points[i+1:]),default=0.)
   good=spread<=max_spread;chosen=points;reason=None
   poses=[p for p in points if p['method']=='pose'];fallbacks=[p for p in points if p['method']=='box_fallback']
   if not good and prefer_pose_on_mixed_conflict and len(poses)==1 and fallbacks and len(poses)+len(fallbacks)==len(points):
    chosen=poses;good=True;reason='mixed_source_conflict'
   samples.append({'frame':frame,'x':median(p['x'] for p in chosen) if good else None,'y':median(p['y'] for p in chosen) if good else None,'status':'research_candidate' if good else 'spatial_conflict','max_spread':spread,'sources':points,'selected_sources':[{'camera':p['camera'],'id':p['id']} for p in chosen] if good else [],'degraded_reason':reason})
  result.append({'id':h['id'],'members':h['members'],'samples':samples})
 return result
