"""Optional direct pose+tracking comparison for one fixed site03 camera.

This experiment does not alter the default detector, association, or quality gates.
"""
from collections import Counter,defaultdict
from pathlib import Path
import csv,hashlib,json,math,sys
import cv2,numpy as np,torch
from scipy.spatial.transform import Rotation
from ultralytics import YOLO,__version__ as ultralytics_version
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));sys.path.insert(0,str(root/'scripts'))
from fetch_site03_sample import FILES,valid
from fetch_site03_calibration import files,valid as valid_calibration
from walkflows.reference_eval import convert_reference,match_positions
from walkflows.artifact_cache import sha256
from walkflows.crossview import local_duplicate_keys
camera='C0001056_v2';raw=root/'data/raw/multiview/006_site03_tracks';assets=root/'data/upstream-research'
video=raw/(camera+'.mp4');reference=raw/'ground-truth.json';weights=root/'data/models/yolo11s-pose.pt'
scene_path=assets/'site03_scene03.json';sensor_path=assets/(camera+'.json')
if not valid(video,FILES[video.name]) or not valid(reference,FILES[reference.name]): raise ValueError('source checksum mismatch')
if sha256(weights)!='1060bda4a27012060eca246f9b2adeea22eabb045a1e58f8d229be29b7ebc2ba': raise ValueError('weights checksum mismatch')
if not valid_calibration(scene_path,files['scenes/site03_scene03.json']) or not valid_calibration(sensor_path,files['binocular/'+camera+'.json']): raise ValueError('calibration checksum mismatch')
if not torch.cuda.is_available(): raise RuntimeError('CUDA required')
scene=json.loads(scene_path.read_text());sensor=json.loads(sensor_path.read_text())['sensor0'];transform=scene['bcam-transforms'][scene['bcam-keys'].index(camera)]
if scene['global-transformation']!={'translation':[0,0,0],'rotation':[0,0,0,1],'scale':1.0} or transform['scale']!=1: raise ValueError('unsupported transform')
ref=json.loads(reference.read_text())['track_results'];parsed=convert_reference(ref)
if ref['frames']!=399 or ref['start-frame']!=0: raise ValueError('unexpected reference coverage')
rotation=Rotation.from_quat(transform['rotation']);C=np.asarray(transform['translation']);scale=np.asarray(sensor['format'])/[896,672];A=np.asarray(sensor['A']);hull=np.asarray(sensor['calib-hull'],dtype=np.float32);bounds=scene['hist-aabb'];exp=np.array([(d-j,j) for d in range(8,-1,-1) for j in range(d+1)])
out=root/'data/processed/site03-direct-pose-probe';out.mkdir(parents=True,exist_ok=True);path=out/'observations.csv'
fields=['frame','local_id','confidence','left','top','right','bottom','ankle_x','ankle_y','ankle_method','floor_x','floor_y','geometry_valid']
model=YOLO(str(weights));cap=cv2.VideoCapture(str(video));rows=[]
try:
 for frame in range(400):
  ok,img=cap.read()
  if not ok or img.shape[:2]!=(672,1792): raise ValueError('unexpected video frame')
  result=model.track(img[:,:896],conf=.1,imgsz=640,classes=[0],device=0,tracker='bytetrack.yaml',persist=True,verbose=False)[0]
  boxes=result.boxes
  if boxes is None or boxes.id is None: continue
  xy=result.keypoints.xy.cpu().tolist() if result.keypoints is not None else []
  scores=result.keypoints.conf.cpu().tolist() if result.keypoints is not None and result.keypoints.conf is not None else []
  for i,(box,score,ident) in enumerate(zip(boxes.xyxy.cpu().tolist(),boxes.conf.cpu().tolist(),boxes.id.cpu().tolist())):
   row={'frame':frame,'local_id':int(ident),'confidence':score,'left':box[0],'top':box[1],'right':box[2],'bottom':box[3],'ankle_x':'','ankle_y':'','ankle_method':'','floor_x':'','floor_y':'','geometry_valid':0}
   pts=[]
   if i<len(xy) and i<len(scores):
    for index in (15,16):
     x,y=xy[i][index];confidence=scores[i][index]
     if confidence>=.5 and 0<=x<896 and 0<=y<672 and (x!=0 or y!=0): pts.append((x,y))
   if pts:
    pixel=np.mean(pts,axis=0);conditioned=(pixel*scale-np.asarray(sensor['center']))*sensor['scale'];uv=A@(conditioned[0]**exp[:,0]*conditioned[1]**exp[:,1]);ray=rotation.apply([*uv,1.0])
    t=-C[2]/ray[2] if abs(ray[2])>1e-8 else float('nan');world=C+t*ray
    good=bool(np.isfinite(world).all() and t>0 and cv2.pointPolygonTest(hull,tuple(pixel*scale),False)>=0 and bounds[0]<=world[0]<=bounds[2] and bounds[1]<=world[1]<=bounds[3])
    row.update(ankle_x=pixel[0],ankle_y=pixel[1],ankle_method='both' if len(pts)==2 else 'one',floor_x=float(world[0]) if np.isfinite(world[0]) else '',floor_y=float(world[1]) if np.isfinite(world[1]) else '',geometry_valid=int(good))
   rows.append(row)
finally: cap.release()
torch.cuda.synchronize()
with path.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
duplicates=local_duplicate_keys([{'frame':x['frame'],'id':x['local_id'],'box':(x['left'],x['top'],x['right'],x['bottom'])} for x in rows],containment=.9)
byframe=defaultdict(list)
for x in rows:
 if x['geometry_valid'] and (x['frame'],x['local_id']) not in duplicates and x['frame'] in parsed['by_frame']: byframe[x['frame']].append({'id':x['local_id'],'x':x['floor_x'],'y':x['floor_y']})
matched=Counter();events=[]
for frame,predictions in sorted(byframe.items()):
 for match in match_positions(predictions,parsed['by_frame'][frame],.5):
  matched[str(match['reference_id'])]+=1;events.append({'frame':frame,**match})
baseline=root/'data/processed/site03-pose-floor'/(camera+'_pose_floor.csv')
base_summary=json.loads((baseline.parent/'summary.json').read_text());base_meta=next(x for x in base_summary['cameras'] if x['camera']==camera)
if sha256(baseline)!=base_meta['output_sha256'] or base_summary['scene_sha256']!=sha256(scene_path): raise ValueError('baseline checksum mismatch')
with baseline.open() as f: base_rows=list(csv.DictReader(f))
base_frames=defaultdict(list)
for x in base_rows:
 frame=int(x['frame'])
 if x['research_candidate']=='1' and frame in parsed['by_frame']: base_frames[frame].append({'id':int(x['local_id']),'x':float(x['floor_x']),'y':float(x['floor_y'])})
base_matches=Counter()
for frame,predictions in base_frames.items():
 for match in match_positions(predictions,parsed['by_frame'][frame],.5): base_matches[str(match['reference_id'])]+=1
report={'scope':'single-camera experimental pose detector/tracker; reference proximity is not identity truth, recall or validated positioning','camera':camera,'video_sha256':sha256(video),'reference_sha256':sha256(reference),'scene_sha256':sha256(scene_path),'sensor_sha256':sha256(sensor_path),'weights_sha256':sha256(weights),'script_sha256':sha256(Path(__file__)),'observations_sha256':sha256(path),'parameters':{'frames':400,'confidence':.1,'imgsz':640,'tracker':'bytetrack.yaml','ankle_threshold':.5,'reference_radius':.5},'versions':{'torch':str(torch.__version__),'ultralytics':ultralytics_version,'opencv':cv2.__version__},'observations':len(rows),'geometry_valid':sum(x['geometry_valid'] for x in rows),'duplicate_excluded':len(duplicates),'baseline_sha256':sha256(baseline),'baseline_valid_comparable':sum(map(len,base_frames.values())),'baseline_reference_proximity_counts':dict(base_matches),'direct_valid_comparable':sum(map(len,byframe.values())),'reference_proximity_counts':dict(matched),'matches':events}
(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='matches'},indent=2))
