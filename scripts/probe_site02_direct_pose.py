"""Compare direct pose tracking with the fixed site02 two-stage baseline."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,math,statistics,sys
import cv2,numpy as np,torch
from scipy.spatial.transform import Rotation
from ultralytics import YOLO,__version__ as ultra_version
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.artifact_cache import sha256
from walkflows.crossview import local_duplicate_keys
from walkflows.reference_eval import match_positions,convert_reference
from walkflows.pose_foot import select_foot
raw=root/'data/raw/multiview/002_site02_gaze';data=root/'data/processed';assets=root/'data/upstream-research';weights=root/'data/models/yolo11s-pose.pt';scene_path=assets/'site02_scene01_v1.json';reference=raw/'ground-truth.json'
expected={'C0001001_v10':'9926ccdd05358cab83c292d9a62f2196961de9439e97857c592a75d2993d5276','C0001011_v10':'1d9b0ff0cbf92d9d107cfb7b197fe393fea5937f1245e5bc99b852e7137c694d'}
if sha256(weights)!='1060bda4a27012060eca246f9b2adeea22eabb045a1e58f8d229be29b7ebc2ba':raise ValueError('weight mismatch')
reference_meta=json.loads((data/'site02-reference-floor/summary.json').read_text())
if sha256(reference)!=reference_meta['source_sha256']:raise ValueError('reference mismatch')
ref=convert_reference(json.loads(reference.read_text())['track_results'])['by_frame']
if set(ref)!=set(range(218)):raise ValueError('reference frames mismatch')
scene=json.loads(scene_path.read_text());pose_summary=json.loads((data/'site02-pose-full/summary.json').read_text());out=data/'site02-direct-pose-holdout';out.mkdir(parents=True,exist_ok=True)
exp=np.array([(d-j,j) for d in range(8,-1,-1) for j in range(d+1)]);reports=[]
for camera,video_hash in expected.items():
 video=raw/(camera+'.mp4');track=data/'site02-gpu-conf010'/(camera+'_observations.csv');pose=data/'site02-pose-full'/(camera+'_track_pose.csv');entry=next(x for x in pose_summary['cameras'] if x['camera']==camera)
 if sha256(video)!=video_hash or sha256(track)!=entry['track_csv_sha256']:raise ValueError('source mismatch')
 sensor_path=assets/(camera+'.json');sensor=json.loads(sensor_path.read_text())['sensor0'];et=scene['bcam-transforms'][scene['bcam-keys'].index(camera)];rot=Rotation.from_quat(et['rotation']);C=np.asarray(et['translation']);scale=np.asarray(sensor['format'])/[896,672];A=np.asarray(sensor['A']);hull=np.asarray(sensor['calib-hull'],dtype=np.float32);bounds=scene['hist-aabb']
 def project(foot):
  if foot is None:return None
  pixel=np.array(foot[:2]);xy=(pixel*scale-np.asarray(sensor['center']))*sensor['scale'];uv=A@(xy[0]**exp[:,0]*xy[1]**exp[:,1]);ray=rot.apply([*uv,1.]);t=-C[2]/ray[2] if abs(ray[2])>1e-8 else float('nan');pos=C+t*ray
  if not (np.isfinite(pos).all() and t>0 and cv2.pointPolygonTest(hull,tuple(pixel*scale),False)>=0 and bounds[0]<=pos[0]<=bounds[2] and bounds[1]<=pos[1]<=bounds[3]):return None
  return float(pos[0]),float(pos[1])
 with track.open() as f:tracks=list(csv.DictReader(f))
 with pose.open() as f:poses=list(csv.DictReader(f))
 pm={(int(x['frame']),int(x['local_id'])):x for x in poses}
 if len(pm)!=len(poses) or len(pm)!=len(tracks):raise ValueError('baseline keys mismatch')
 baseline=[]
 for t in tracks:
  frame=int(t['frame']);ident=int(t['local_id']);x=pm[(frame,ident)];row={'status':x['match_status']}
  for side in ('left','right'):
   for field in ('x','y','confidence'):row[side+'_'+field]=x[side+'_ankle_'+field]
  baseline.append({'frame':frame,'id':ident,'box':tuple(float(t[k]) for k in ('left','top','right','bottom')),'point':project(select_foot(row,threshold=.5,width=896,height=672))})
 model=YOLO(str(weights));cap=cv2.VideoCapture(str(video));direct=[]
 try:
  for frame in range(218):
   ok,img=cap.read()
   if not ok or img.shape[:2]!=(672,1792):raise ValueError('invalid frame')
   r=model.track(img[:,:896],conf=.1,imgsz=640,classes=[0],device=0,tracker='bytetrack.yaml',persist=True,verbose=False)[0]
   if r.boxes is None or r.boxes.id is None:continue
   xy=r.keypoints.xy.cpu().tolist() if r.keypoints is not None else [];conf=r.keypoints.conf.cpu().tolist() if r.keypoints is not None and r.keypoints.conf is not None else []
   for i,(box,ident) in enumerate(zip(r.boxes.xyxy.cpu().tolist(),r.boxes.id.cpu().tolist())):
    row={'status':'unique'}
    if i<len(xy) and i<len(conf):
     for side,j in [('left',15),('right',16)]:row.update({side+'_x':xy[i][j][0],side+'_y':xy[i][j][1],side+'_confidence':conf[i][j]})
    direct.append({'frame':frame,'id':int(ident),'box':box,'point':project(select_foot(row,threshold=.5,width=896,height=672))})
 finally:cap.release()
 torch.cuda.synchronize()
 def evaluate(rows):
  dup=local_duplicate_keys([{'frame':x['frame'],'id':x['id'],'box':x['box']} for x in rows],containment=.9);byframe=defaultdict(list)
  for x in rows:
   if x['point'] is not None and (x['frame'],x['id']) not in dup:byframe[x['frame']].append({'id':x['id'],'x':x['point'][0],'y':x['point'][1]})
  matches=[]
  for frame,points in sorted(byframe.items()):
   
   for m in match_positions(points,ref[frame],.5):
    point=next(x for x in points if x['id']==m['prediction_id']);matches.append({'frame':frame,**m,'x':point['x'],'y':point['y']})
  counts=Counter(m['prediction_id'] for m in matches)
  return {'observations':len(rows),'duplicate_excluded':len(dup),'valid_points':sum(map(len,byframe.values())),'matched_frames':len(matches),'unmatched_predictions':sum(map(len,byframe.values()))-len(matches),'reference_without_match':218-len(matches),'local_id_support':dict(counts),'median_distance':statistics.median(m['distance'] for m in matches) if matches else None,'matches':matches}
 b=evaluate(baseline);d=evaluate(direct)
 report={'camera':camera,'video_sha256':sha256(video),'calibration_sha256':sha256(sensor_path),'baseline_track_sha256':sha256(track),'baseline_pose_sha256':sha256(pose),'baseline':b,'direct':d};reports.append(report)
 print(camera,'baseline', {k:v for k,v in b.items() if k!='matches'},'direct',{k:v for k,v in d.items() if k!='matches'},flush=True)
paired={}
for camera in reports:
 b={m['frame']:m for m in camera['baseline']['matches']};d={m['frame']:m for m in camera['direct']['matches']};common=b.keys()&d.keys()
 paired[camera['camera']]={'common_frames':len(common),'baseline_median':statistics.median(b[f]['distance'] for f in common) if common else None,'direct_median':statistics.median(d[f]['distance'] for f in common) if common else None,'direct_only_frames':len(d.keys()-b.keys()),'baseline_only_frames':len(b.keys()-d.keys())}
cross={}
for method in ('baseline','direct'):
 a={m['frame']:m for m in reports[0][method]['matches']};b={m['frame']:m for m in reports[1][method]['matches']};frames=sorted(a.keys()&b.keys());dist=[math.hypot(a[f]['x']-b[f]['x'],a[f]['y']-b[f]['y']) for f in frames]
 cross[method]={'common_reference_near_frames':len(frames),'median_pair_distance':statistics.median(dist) if dist else None,'frames':frames}
result={'paired_support':paired,'cross_camera':cross,'scope':'site02 cross-scene research comparison; reference visibility and identity unknown, not precision/recall','weights_sha256':sha256(weights),'reference_sha256':sha256(reference),'scene_sha256':sha256(scene_path),'script_sha256':sha256(Path(__file__)),'parameters':{'frame_count':218,'confidence':.1,'imgsz':640,'tracker':'bytetrack.yaml','ankle_threshold':.5,'reference_radius':.5},'versions':{'torch':str(torch.__version__),'ultralytics':ultra_version,'opencv':cv2.__version__},'cameras':reports}
(out/'report.json').write_text(json.dumps(result,indent=2))
