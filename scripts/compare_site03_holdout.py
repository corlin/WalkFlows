"""Compare two fixed tracking pipelines on the separate site03 007 clip."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,math,statistics,sys
import cv2,numpy as np,torch
from scipy.spatial.transform import Rotation
from ultralytics import YOLO,__version__ as ultra_version
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));sys.path.insert(0,str(root/'scripts'))
from fetch_site03_holdout import FILES,OUT
from fetch_site03_sample import valid
from fetch_site03_calibration import files as calibrations,valid as valid_calibration
from walkflows.artifact_cache import sha256
from walkflows.crossview import local_duplicate_keys
from walkflows.reference_eval import convert_reference,match_positions
from walkflows.pose_foot import select_foot
assets=root/'data/upstream-research';scene_path=assets/'site03_scene03.json';reference=OUT/'ground-truth.json';manifest=OUT/'manifest.json';models=root/'data/models';out=root/'data/processed/site03-007-comparison';out.mkdir(parents=True,exist_ok=True)
for name in ('ground-truth.json','manifest.json','C0001055_v4.mp4','C0001056_v2.mp4'):
 if not valid(OUT/name,FILES[name]):raise ValueError('sample mismatch '+name)
expected={'yolo11n.pt':'0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1','yolo11n-pose.pt':'869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0','yolo11s-pose.pt':'1060bda4a27012060eca246f9b2adeea22eabb045a1e58f8d229be29b7ebc2ba'}
if any(sha256(models/n)!=h for n,h in expected.items()):raise ValueError('model mismatch')
if not valid_calibration(scene_path,calibrations['scenes/site03_scene03.json']):raise ValueError('scene mismatch')
scene=json.loads(scene_path.read_text());manifest_data=json.loads(manifest.read_text());ref_data=json.loads(reference.read_text())['track_results'];ref=convert_reference(ref_data)['by_frame']
if manifest_data['scene-key']!='site03_scene03' or ref_data['frames']!=500 or ref_data['start-frame']!=0:raise ValueError('unexpected data contract')
exp=np.array([(d-j,j) for d in range(8,-1,-1) for j in range(d+1)])
def iou(a,b):
 intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
 return intersection/union if union>0 else 0
reports=[]
for camera in ('C0001055_v4','C0001056_v2'):
 sensor_path=assets/(camera+'.json')
 if not valid_calibration(sensor_path,calibrations['binocular/'+camera+'.json']):raise ValueError('calibration mismatch')
 sensor=json.loads(sensor_path.read_text())['sensor0'];et=scene['bcam-transforms'][scene['bcam-keys'].index(camera)];rot=Rotation.from_quat(et['rotation']);C=np.asarray(et['translation']);scale=np.asarray(sensor['format'])/[896,672];A=np.asarray(sensor['A']);hull=np.asarray(sensor['calib-hull'],dtype=np.float32);bounds=scene['hist-aabb']
 def project(row):
  foot=select_foot(row,threshold=.5,width=896,height=672)
  if foot is None:return None
  pixel=np.array(foot[:2]);xy=(pixel*scale-np.asarray(sensor['center']))*sensor['scale'];uv=A@(xy[0]**exp[:,0]*xy[1]**exp[:,1]);ray=rot.apply([*uv,1.]);t=-C[2]/ray[2] if abs(ray[2])>1e-8 else float('nan');pos=C+t*ray
  if not (np.isfinite(pos).all() and t>0 and cv2.pointPolygonTest(hull,tuple(pixel*scale),False)>=0 and bounds[0]<=pos[0]<=bounds[2] and bounds[1]<=pos[1]<=bounds[3]):return None
  return [float(pos[0]),float(pos[1])]
 methods={}
 for method in ('baseline','direct'):
  detector=YOLO(str(models/('yolo11n.pt' if method=='baseline' else 'yolo11s-pose.pt')));pose=YOLO(str(models/'yolo11n-pose.pt')) if method=='baseline' else None
  cap=cv2.VideoCapture(str(OUT/(camera+'.mp4')));rows=[]
  try:
   for frame in range(500):
    ok,img=cap.read()
    if not ok or img.shape[:2]!=(672,1792):raise ValueError('invalid frame')
    track=detector.track(img[:,:896],conf=.1,imgsz=640,classes=[0],device=0,tracker='bytetrack.yaml',persist=True,verbose=False)[0]
    if track.boxes is None or track.boxes.id is None:continue
    tb=track.boxes.xyxy.cpu().tolist();ids=track.boxes.id.cpu().tolist()
    result=pose.predict(img[:,:896],conf=.1,imgsz=640,classes=[0],device=0,verbose=False)[0] if pose else track
    pb=result.boxes.xyxy.cpu().tolist();xy=result.keypoints.xy.cpu().tolist() if result.keypoints is not None else [];scores=result.keypoints.conf.cpu().tolist() if result.keypoints is not None and result.keypoints.conf is not None else []
    if pose:
     edges=[(i,j) for i,a in enumerate(tb) for j,b in enumerate(pb) if iou(a,b)>=.5];left=Counter(i for i,j in edges);right=Counter(j for i,j in edges);mapping={i:j for i,j in edges if left[i]==1 and right[j]==1}
    else:mapping={i:i for i in range(len(tb))}
    for i,(box,ident) in enumerate(zip(tb,ids)):
     row={'status':'unique' if i in mapping else 'no_candidate'};j=mapping.get(i,-1)
     if 0<=j<len(xy) and j<len(scores):
      for side,index in (('left',15),('right',16)):row.update({side+'_x':xy[j][index][0],side+'_y':xy[j][index][1],side+'_confidence':scores[j][index]})
     rows.append({'frame':frame,'id':int(ident),'box':box,'point':project(row)})
  finally:cap.release()
  torch.cuda.synchronize();dups=local_duplicate_keys([{'frame':x['frame'],'id':x['id'],'box':x['box']} for x in rows],containment=.9);byframe=defaultdict(list)
  for row in rows:
   if row['point'] is not None and (row['frame'],row['id']) not in dups:byframe[row['frame']].append({'id':row['id'],'x':row['point'][0],'y':row['point'][1]})
  matches=[]
  for frame,points in sorted(byframe.items()):
   for m in match_positions(points,ref[frame],.5):matches.append({'frame':frame,**m})
  eligible=[{'camera':camera,'id':x['id'],'frame':x['frame'],'x':x['point'][0],'y':x['point'][1]} for x in rows if x['point'] is not None and (x['frame'],x['id']) not in dups]
  evidence=out/(camera+'_'+method+'_floor.json');evidence.write_text(json.dumps(eligible,indent=2,allow_nan=False))
  methods[method]={'floor_sha256':sha256(evidence),'observations':len(rows),'duplicate_excluded':len(dups),'valid_points':sum(map(len,byframe.values())),'matched_observations':len(matches),'matched_distinct_frames':len({m['frame'] for m in matches}),'matched_by_reference':dict(Counter(m['reference_id'] for m in matches)),'median_distance':statistics.median(m['distance'] for m in matches) if matches else None,'matches':matches}
  print(camera,method,{k:v for k,v in methods[method].items() if k!='matches'},flush=True)
 base={(m['frame'],m['reference_id']):m for m in methods['baseline']['matches']};direct={(m['frame'],m['reference_id']):m for m in methods['direct']['matches']};common=base.keys()&direct.keys()
 paired={'common_frame_reference_pairs':len(common),'baseline_median_distance':statistics.median(base[k]['distance'] for k in common) if common else None,'direct_median_distance':statistics.median(direct[k]['distance'] for k in common) if common else None,'direct_only_pairs':len(direct.keys()-base.keys()),'baseline_only_pairs':len(base.keys()-direct.keys())}
 reports.append({'camera':camera,'video_sha256':sha256(OUT/(camera+'.mp4')),'sensor_sha256':sha256(sensor_path),'methods':methods,'paired':paired});print(camera,'paired',paired,flush=True)
result={'scope':'separate same-site 007 clip; exploratory proximity, not identity truth, recall or customer count','script_sha256':sha256(Path(__file__)),'reference_sha256':sha256(reference),'manifest_sha256':sha256(manifest),'scene_sha256':sha256(scene_path),'models':expected,'versions':{'torch':str(torch.__version__),'ultralytics':ultra_version,'opencv':cv2.__version__},'parameters':{'frames':500,'confidence':.1,'imgsz':640,'tracker':'bytetrack.yaml','ankle_threshold':.5,'reference_radius':.5},'cameras':reports}
(out/'report.json').write_text(json.dumps(result,indent=2))
