"""Offline appearance guard applied to relaxed ByteTrack results; research only."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,hashlib,json,sys
import cv2
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.track_gap_guard import segment_track,normalize,distance
from walkflows.tracker_comparison import iou
from walkflows.association_diagnostic import diagnose
from walkflows.reference_eval import convert_reference
p=root/'data/processed';exp=p/'site03-byte095-experiment';hpath=p/'site03-hypotheses/hypotheses.json';rpath=p/'site03-review/data.json';raw=root/'data/raw/multiview/006_site03_tracks';refpath=raw/'ground-truth.json';sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
h=json.loads(hpath.read_text());review=json.loads(rpath.read_text());refs=convert_reference(json.loads(refpath.read_text())['track_results'])['by_frame'];observations=[]
for hypothesis in h['hypotheses']:
 for sample in hypothesis['samples']:
  for source in sample['sources']:observations.append(dict(frame=sample['frame'],**source))
proxy={(x['camera'],x['frame'],x['id']):x for x in diagnose(observations,refs,.5)};results=[]
for cam in ('C0001055_v4','C0001056_v2'):
 trackpath=exp/(cam+'_observations.csv');meta=json.loads((exp/(cam+'_run.json')).read_text());video=raw/(cam+'.mp4')
 if sha(trackpath)!=meta['observations_sha256'] or sha(video)!=meta['contract']['video_sha256']:raise ValueError('input checksum mismatch')
 with trackpath.open() as f:rows=[{k:int(v) if k in ('frame','local_id') else float(v) for k,v in r.items()} for r in csv.DictReader(f)]
 byframe=defaultdict(list)
 for row in rows:byframe[row['frame']].append(row)
 cap=cv2.VideoCapture(str(video));tracks=defaultdict(list);decoded=0
 try:
  while True:
   ok,img=cap.read()
   if not ok:break
   if img.shape[:2]!=(672,1792):raise ValueError('unexpected video format')
   for row in byframe[decoded]:
    x1,y1,x2,y2=[row[k] for k in ('left','top','right','bottom')];w=x2-x1;h=y2-y1
    patch=img[max(0,int(y1+.22*h)):min(672,int(y1+.60*h)),max(0,int(x1+.20*w)):min(896,int(x2-.20*w))]
    feature=None
    if patch.size:
     hsv=cv2.cvtColor(patch,cv2.COLOR_BGR2HSV);hist=cv2.calcHist([hsv],[0,1],None,[12,8],[0,180,0,256]);feature=hist.reshape(-1).astype(float).tolist()
    tracks[row['local_id']].append({'frame':decoded,'feature':feature,'box':row})
   decoded+=1
 finally:cap.release()
 if decoded!=400 or sum(map(len,tracks.values()))!=len(rows):raise ValueError('decoded frame or observation mismatch')
 output=[];segment_by_key={};splits=[]
 for ident,items in sorted(tracks.items()):
  segments=segment_track(items,.6)
  for index,(item,segment) in enumerate(zip(items,segments,strict=True)):
   key=(item['frame'],ident);segment_by_key[key]=segment;output.append({'frame':item['frame'],'local_id':ident,'segment':segment})
   if index and segments[index-1]!=segment:
    previous=items[index-1];a=normalize(previous['feature']);b=normalize(item['feature']);splits.append({'local_id':ident,'previous_frame':previous['frame'],'next_frame':item['frame'],'appearance_distance':distance(a,b),'reason':'appearance_unavailable' if a is None or b is None else 'appearance_conflict'})
 evidence=defaultdict(Counter);baseframes=defaultdict(list)
 for r in review['cameras'][cam]:baseframes[r['frame']].append(r)
 for r in review['cameras'][cam]:
  match=proxy.get((cam,r['frame'],r['id']))
  if not match or match['status']!='matched':continue
  box=dict(zip(('left','top','right','bottom'),r['box']));candidates=[z for z in byframe[r['frame']] if iou(box,z)>=.8]
  if len(candidates)!=1:continue
  v=candidates[0];competitors=[z for z in baseframes[r['frame']] if iou(dict(zip(('left','top','right','bottom'),z['box'])),v)>=.8]
  if len(competitors)!=1:continue
  evidence[(v['local_id'],segment_by_key[(v['frame'],v['local_id'])])][match['reference_id']]+=1
 results.append({'camera':cam,'observations':len(rows),'segments':len(set((x['local_id'],x['segment']) for x in output)),'splits':splits,'reference_proxy_support':[{'local_id':k[0],'segment':k[1],'support':dict(sorted(v.items()))} for k,v in sorted(evidence.items())],'observations_sha256':sha(trackpath),'video_sha256':sha(video),'assignments':output})
report={'scope':'Experimental color conflict guard; no identity validation, track counts, or customer counts.','threshold':.6,'gap_required':True,'inputs':{'hypotheses_sha256':sha(hpath),'review_sha256':sha(rpath),'reference_sha256':sha(refpath)},'limitations':['Threshold selected on these same examples; not held-out evaluation.','Color can change with lighting, occlusion and pose; same color does not imply identity.','Consecutive-frame switches are not examined; gaps are not interpolated.'],'cameras':results}
(exp/'gap-guard.json').write_text(json.dumps(report,indent=2,allow_nan=False));print(json.dumps([dict(camera=x['camera'],observations=x['observations'],segments=x['segments'],splits=x['splits'],reference_proxy_support=x['reference_proxy_support']) for x in results],indent=2))
