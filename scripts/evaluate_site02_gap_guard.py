"""Frozen site03 appearance-gap rule on held-out site02 track observations."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,sys
import cv2
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.track_gap_guard import normalize,distance,segment_track
out=root/'data/processed/site02-byte095-holdout';raw=root/'data/raw/multiview/002_site02_gaze';meta=json.loads((out/'run.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();results=[]
config=root/'data/processed/site03-byte095-experiment/byte095.yaml'
if sha(config)!=meta['tracker_config_sha256']:raise ValueError('tracker config hash mismatch')
for entry in meta['runs']:
 cam=entry['camera'];video=raw/(cam+'.mp4');path=out/(cam+'_observations.csv')
 if sha(video)!=entry['sha256'] or sha(path)!=entry['observations_sha256']:raise ValueError('video or tracking hash mismatch')
 with path.open() as f:rows=list(csv.DictReader(f))
 if len(rows)!=entry['observations']:raise ValueError('observation count mismatch')
 frames=defaultdict(list)
 for r in rows:frames[int(r['frame'])].append(r)
 cap=cv2.VideoCapture(str(video));tracks=defaultdict(list);n=0
 try:
  while True:
   ok,img=cap.read()
   if not ok:break
   if img.shape[:2]!=(672,1792):raise ValueError('invalid frame')
   for r in frames[n]:
    x1,y1,x2,y2=[float(r[k]) for k in ('left','top','right','bottom')];w=x2-x1;h=y2-y1;patch=img[max(0,int(y1+.22*h)):min(672,int(y1+.60*h)),max(0,int(x1+.20*w)):min(896,int(x2-.20*w))];feature=None
    if patch.size:
     hsv=cv2.cvtColor(patch,cv2.COLOR_BGR2HSV);feature=cv2.calcHist([hsv],[0,1],None,[12,8],[0,180,0,256]).reshape(-1).astype(float).tolist()
    tracks[int(r['local_id'])].append({'frame':n,'feature':feature})
   n+=1
 finally:cap.release()
 if n!=entry['frames'] or sum(map(len,tracks.values()))!=len(rows):raise ValueError('frame or observation mismatch')
 gaps=[]
 for ident,items in sorted(tracks.items()):
  segments=segment_track(items,.6)
  for i in range(1,len(items)):
   a,b=items[i-1],items[i]
   if b['frame']>a['frame']+1:gaps.append({'local_id':ident,'previous_frame':a['frame'],'next_frame':b['frame'],'distance':distance(normalize(a['feature']),normalize(b['feature'])),'split':segments[i]!=segments[i-1]})
 results.append({'camera':cam,'video_sha256':sha(video),'tracks_sha256':sha(path),'observations':len(rows),'frames':n,'gaps':gaps})
result={'scope':'Held-out scene gap candidates, no independent identity labels; not accuracy or false-split rate.','threshold':.6,'cameras':results};(out/'gap-guard.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
