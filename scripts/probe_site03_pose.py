"""Site03 pose evidence with per-camera, content-verified resumable cache."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,json,os,sys,time
import cv2,torch
from ultralytics import YOLO,__version__ as ultralytics_version
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));sys.path.insert(0,str(root/'scripts'))
from fetch_site03_sample import FILES,valid
from walkflows.artifact_cache import cache_valid,sha256
weights=root/'data/models/yolo11n-pose.pt';expected='869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0'
if sha256(weights)!=expected:raise ValueError('pose weight checksum mismatch')
if not torch.cuda.is_available():raise RuntimeError('CUDA required')
out=root/'data/processed/site03-pose-evidence';out.mkdir(parents=True,exist_ok=True)
fields=['frame','local_id','status','pose_index','iou','pose_confidence','left_x','left_y','left_confidence','right_x','right_y','right_confidence']
def iou(a,b):
 intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
 return intersection/union if union>0 else 0
model=None;summary=[];script_sha=sha256(Path(__file__))
for name,meta in FILES.items():
 if not name.endswith('.mp4'):continue
 camera=name[:-4];src=root/'data/raw/multiview/006_site03_tracks'/name;track=root/'data/processed/site03-gpu-conf010'/(camera+'_observations.csv');run=root/'data/processed/site03-gpu-conf010'/(camera+'_run.json')
 if not valid(src,meta) or sha256(track)!=json.loads(run.read_text())['observations_sha256']:raise ValueError('input mismatch '+camera)
 contract={'camera':camera,'video_sha256':meta[1],'track_sha256':sha256(track),'weight_sha256':expected,'script_sha256':script_sha,'torch':str(torch.__version__),'cuda':str(torch.version.cuda),'device':torch.cuda.get_device_name(0),'opencv':cv2.__version__,'ultralytics':ultralytics_version,'conf':.1,'imgsz':640,'iou_threshold':.5,'frame_count':400}
 dest=out/(camera+'_track_pose.csv');cache=out/(camera+'_run.json')
 if cache_valid(cache,contract,out,(dest.name,)):
  result=json.loads(cache.read_text())['result'];summary.append(result);print(camera+' pose cache verified',flush=True);continue
 with track.open() as f:tracks=list(csv.DictReader(f))
 by_frame=defaultdict(list)
 for row in tracks:
  frame=int(row['frame'])
  if not 0<=frame<400:raise ValueError('track frame outside clip')
  by_frame[frame].append(row)
 cap=cv2.VideoCapture(str(src));rows=[];index=0;start=time.perf_counter();processed=0
 if not cap.isOpened():raise ValueError('cannot open video '+camera)
 try:
  while True:
   ok,frame=cap.read()
   if not ok:break
   if frame.shape[:2]!=(672,1792):raise ValueError('unexpected input dimensions')
   current=by_frame[index]
   if current:
    if model is None:model=YOLO(str(weights))
    pose=model.predict(frame[:,:896],device=0,conf=.1,imgsz=640,verbose=False)[0];boxes=pose.boxes.xyxy.cpu().tolist();scores=pose.boxes.conf.cpu().tolist();xy=pose.keypoints.xy.cpu().tolist() if pose.keypoints is not None else [];conf=pose.keypoints.conf.cpu().tolist() if pose.keypoints is not None and pose.keypoints.conf is not None else [];processed+=1
    tboxes=[[float(t[k]) for k in ('left','top','right','bottom')] for t in current];edges=[(i,j,iou(a,b)) for i,a in enumerate(tboxes) for j,b in enumerate(boxes) if iou(a,b)>=.5];tc=Counter(i for i,j,_ in edges);pc=Counter(j for i,j,_ in edges);matches={i:(j,d) for i,j,d in edges if tc[i]==1 and pc[j]==1}
    for i,trackrow in enumerate(current):
     row={k:'' for k in fields};row.update(frame=index,local_id=int(trackrow['local_id']),status='unique' if i in matches else 'ambiguous' if tc[i] else 'no_candidate')
     if i in matches:
      j,d=matches[i];row.update(pose_index=j,iou=d,pose_confidence=scores[j])
      if j<len(xy) and j<len(conf) and len(xy[j])>=17 and len(conf[j])>=17:row.update(left_x=xy[j][15][0],left_y=xy[j][15][1],left_confidence=conf[j][15],right_x=xy[j][16][0],right_y=xy[j][16][1],right_confidence=conf[j][16])
     rows.append(row)
   index+=1
 finally:cap.release()
 torch.cuda.synchronize()
 if index!=400 or len(rows)!=len(tracks):raise ValueError('frame or track coverage mismatch '+camera)
 tmp=dest.with_suffix('.csv.tmp')
 with tmp.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 os.replace(tmp,dest)
 result={'camera':camera,'video_sha256':meta[1],'track_sha256':sha256(track),'pose_csv_sha256':sha256(dest),'decoded_frames':index,'inference_frames':processed,'observations':len(rows),'status_counts':dict(Counter(x['status'] for x in rows)),'seconds':time.perf_counter()-start}
 cache_data={'contract':contract,'artifacts':{dest.name:result['pose_csv_sha256']},'result':result};tmp=cache.with_suffix('.json.tmp');tmp.write_text(json.dumps(cache_data,indent=2));os.replace(tmp,cache)
 summary.append(result);print(json.dumps(result),flush=True)
result={'scope':'Pose box overlap candidates only; keypoint scores are uncalibrated and not verified visibility. No tracking or quality gate changes.','weight_sha256':expected,'script_sha256':script_sha,'opencv':cv2.__version__,'ultralytics':ultralytics_version,'torch':str(torch.__version__),'conf':.1,'imgsz':640,'iou_threshold':.5,'cameras':summary}
tmp=out/'summary.json.tmp';tmp.write_text(json.dumps(result,indent=2));os.replace(tmp,out/'summary.json')
