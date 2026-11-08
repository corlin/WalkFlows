"""Short overlapping-box tracklet handoff candidates; not identity truth."""
from collections import defaultdict,Counter
from itertools import combinations
from statistics import median
from walkflows.tracker_comparison import iou

def propose_links(rows,*,min_shared,max_shared,iou_threshold):
 if type(min_shared) is not int or type(max_shared) is not int or min_shared<1 or max_shared<min_shared or isinstance(iou_threshold,bool) or not isinstance(iou_threshold,(int,float)) or not 0<iou_threshold<=1:raise ValueError('invalid settings')
 tracks=defaultdict(dict)
 for r in rows:
  cam,ident,frame=r['camera'],r['local_id'],r['frame'];key=(cam,ident)
  if not isinstance(cam,str) or not cam or type(ident) is not int or ident<0 or type(frame) is not int or frame<0 or frame in tracks[key] or not r['left']<r['right'] or not r['top']<r['bottom']:raise ValueError('invalid observation')
  tracks[key][frame]=r
 edges=[]
 for a,b in combinations(sorted(tracks),2):
  if a[0]!=b[0]:continue
  ta,tb=tracks[a],tracks[b];aa,ab=min(ta),max(ta);ba,bb=min(tb),max(tb)
  if aa<ba and ab<bb:left,right=a,b
  elif ba<aa and bb<ab:left,right=b,a
  else:continue
  common=sorted(set(tracks[left])&set(tracks[right]))
  if len(common)<min_shared or len(common)>max_shared:continue
  scores=[iou(tracks[left][f],tracks[right][f]) for f in common];support=[f for f,v in zip(common,scores) if v>=iou_threshold]
  if len(support)<min_shared:continue
  edges.append({'camera':left[0],'from_id':left[1],'to_id':right[1],'shared_frames':common,'support_frames':support,'median_iou':median(scores)})
 outgoing=Counter((e['camera'],e['from_id']) for e in edges);incoming=Counter((e['camera'],e['to_id']) for e in edges)
 for e in edges:e['status']='candidate' if outgoing[(e['camera'],e['from_id'])]==1 and incoming[(e['camera'],e['to_id'])]==1 else 'ambiguous'
 return sorted(edges,key=lambda e:(e['camera'],e['from_id'],e['to_id']))
