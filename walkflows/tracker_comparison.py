"""Frame-local mutual uniqueness comparisons, not tracking accuracy."""
from collections import Counter,defaultdict
from math import isfinite

def iou(a,b):
 w=max(0,min(a['right'],b['right'])-max(a['left'],b['left']))
 h=max(0,min(a['bottom'],b['bottom'])-max(a['top'],b['top']))
 intersection=w*h
 area=lambda r:(r['right']-r['left'])*(r['bottom']-r['top'])
 return intersection/(area(a)+area(b)-intersection) if intersection else 0.

def compare(left,right,threshold):
 if not isfinite(threshold) or not 0 < threshold <= 1: raise ValueError('invalid IoU threshold')
 for group in (left,right):
  seen=set()
  for r in group:
   key=(r['frame'],r['local_id'])
   if key in seen or r['left']>=r['right'] or r['top']>=r['bottom'] or not all(isfinite(r[k]) for k in ('left','top','right','bottom')): raise ValueError('invalid track box')
   seen.add(key)
 by_frame=defaultdict(list)
 for j,r in enumerate(right):by_frame[r['frame']].append(j)
 l_edges=defaultdict(list);r_edges=defaultdict(list)
 for i,a in enumerate(left):
  for j in by_frame[a['frame']]:
   if iou(a,right[j])>=threshold:l_edges[i].append(j);r_edges[j].append(i)
 lc=Counter();rc=Counter();pairs=Counter()
 for i,a in enumerate(left):
  links=l_edges[i]
  if not links:lc['no_candidate']+=1
  elif len(links)!=1 or len(r_edges[links[0]])!=1:lc['ambiguous']+=1
  else:lc['unique']+=1;pairs[(a['local_id'],right[links[0]]['local_id'])]+=1
 for j in range(len(right)):
  links=r_edges[j]
  if not links:rc['no_candidate']+=1
  elif len(links)!=1 or len(l_edges[links[0]])!=1:rc['ambiguous']+=1
  else:rc['unique']+=1
 return {'left_status':dict(lc),'right_status':dict(rc),'pairs':[{'left_id':a,'right_id':b,'frames':n} for (a,b),n in sorted(pairs.items())]}
