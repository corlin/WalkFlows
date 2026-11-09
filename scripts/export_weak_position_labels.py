"""Export unique spatial-proxy pairs for one train or validation scenario.

Pairs are weak labels, not independently verified per-camera identity.
"""
from pathlib import Path
import argparse,json,math,os,re,sys
import cv2,numpy as np,torch
from scipy.spatial.transform import Rotation
from ultralytics import YOLO,__version__ as ultra_version
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.artifact_cache import sha256,cache_valid
from walkflows.crossview import local_duplicate_keys
from walkflows.floor_projection import project_pixel
from walkflows.pose_foot import select_foot
from walkflows.reference_eval import convert_reference
from walkflows.scene_transforms import compose_camera,normalized_bounds
from walkflows.weak_supervision import unique_position_pairs
from walkflows.scenario_names import valid_scenario_name
from scripts.fetch_multiview_dataset import digest
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--scenario',required=True);parser.add_argument('--camera');args=parser.parse_args()
if not valid_scenario_name(args.scenario):parser.error('invalid scenario name')
state=root/'data/processed/multiview-inventory';raw=root/'data/raw/multiview/full-dataset';inventory=json.loads((state/'manifest.json').read_text());split_data=json.loads((state/'site-splits.json').read_text())
if split_data['manifest_sha256']!=sha256(state/'manifest.json') or inventory['revision']!=split_data['revision']:raise ValueError('stale split manifest')
entries={x['path']:x for x in inventory['entries']};prefix='testcases/'+args.scenario+'/';manifest_path=prefix+'manifest.json';reference_path=prefix+'ground-truth.json'
roles=[name for name in ('train','validation','test') if manifest_path in {x['path'] for x in split_data['splits'][name]}]
if len(roles)!=1 or roles[0]=='test':raise ValueError('scenario must belong to training or validation; test data is reserved')
role=roles[0]
def read(path):
 if path not in entries or not digest(raw/path,entries[path]):raise ValueError('missing or unverified input '+path)
 return json.loads((raw/path).read_text())
manifest=read(manifest_path);reference=read(reference_path)['track_results'];refs=convert_reference(reference)['by_frame'];frames=reference['frames']
if type(reference.get('start-frame')) is not int or reference['start-frame']<0:raise ValueError('invalid reference start metadata')
scene_path='calibration/scenes/'+manifest['scene-key']+'.json';scene=read(scene_path);bounds=normalized_bounds(scene['hist-aabb']);origin=reference['top-left'];step=reference['hist-sz'];expected=[origin[0],origin[1],origin[0]+reference['width']*step,origin[1]+reference['height']*step]
if not np.allclose(bounds,expected,atol=step+1e-5,rtol=0):raise ValueError('scene/reference bounds mismatch beyond one grid cell')
global_t=scene['global-transformation'];vertical=Rotation.from_quat(global_t['rotation']).apply([0,0,1])
if not np.allclose(vertical,[0,0,1],atol=1e-8,rtol=0) or abs(global_t['translation'][2])>1e-8:raise ValueError('unsupported tilted or shifted ground plane')
weights=root/'data/models/yolo11s-pose.pt';expected_weight='1060bda4a27012060eca246f9b2adeea22eabb045a1e58f8d229be29b7ebc2ba'
if sha256(weights)!=expected_weight or not torch.cuda.is_available():raise ValueError('pinned model or CUDA unavailable')
cameras={x['camera']:x for x in manifest['videos']};selected=[args.camera] if args.camera else sorted(cameras)
if not set(selected)<=set(cameras):raise ValueError('camera absent from manifest')
output=root/'data/processed/weak-position-labels'/args.scenario;output.mkdir(parents=True,exist_ok=True);model=None
for camera in selected:
 video_entry=cameras[camera];video_path=prefix+video_entry['file'];sensor_path='calibration/binocular/'+camera+'.json';sensor=read(sensor_path)['sensor0'];video=raw/video_path
 if video_path not in entries or not digest(video,entries[video_path]):raise ValueError('missing or corrupt video '+video_path)
 if camera not in scene['bcam-keys'] or not math.isclose(video_entry['fps']*reference['frame-duration'],1,abs_tol=1e-5):raise ValueError('camera or fps mismatch')
 transform=compose_camera(scene['bcam-transforms'][scene['bcam-keys'].index(camera)],global_t)
 contract={'split':role,'scenario':args.scenario,'camera':camera,'inventory_sha256':sha256(state/'manifest.json'),'splits_sha256':sha256(state/'site-splits.json'),'manifest_sha256':sha256(raw/manifest_path),'reference_sha256':sha256(raw/reference_path),'scene_sha256':sha256(raw/scene_path),'sensor_sha256':sha256(raw/sensor_path),'video_sha256':sha256(video),'weights_sha256':expected_weight,'script_sha256':sha256(Path(__file__)),'scenario_validator_sha256':sha256(root/'walkflows/scenario_names.py'),'fps':video_entry['fps'],'frames':frames,'reference_start_frame':reference['start-frame'],'frame_index_policy':'clip_relative_reference_path','confidence':.1,'imgsz':640,'ankle_threshold':.5,'distance_gate':.5,'torch':str(torch.__version__),'ultralytics':ultra_version,'opencv':cv2.__version__}
 dest=output/(camera+'.jsonl');cache=output/(camera+'.cache.json')
 if cache_valid(cache,contract,output,(dest.name,)):
  print(camera,'verified cache',flush=True);continue
 if model is None:model=YOLO(str(weights))
 cap=cv2.VideoCapture(str(video));rows=[];total_pred=total_valid=total_pairs=0
 try:
  for frame in range(frames):
   ok,img=cap.read()
   if not ok or img.shape[:2]!=(672,1792):raise ValueError('invalid stereo frame')
   result=model.predict(img[:,:896],conf=.1,imgsz=640,classes=[0],device=0,verbose=False)[0]
   boxes=result.boxes.xyxy.cpu().tolist();scores=result.boxes.conf.cpu().tolist();xy=result.keypoints.xy.cpu().tolist() if result.keypoints is not None else [];conf=result.keypoints.conf.cpu().tolist() if result.keypoints is not None and result.keypoints.conf is not None else []
   duplicate=local_duplicate_keys([{'frame':frame,'id':i,'box':b} for i,b in enumerate(boxes)],containment=.9);predictions=[]
   for i,(box,score) in enumerate(zip(boxes,scores)):
    if (frame,i) in duplicate:continue
    row={'status':'unique'}
    if i<len(xy) and i<len(conf):
     for side,j in (('left',15),('right',16)):row.update({side+'_x':xy[i][j][0],side+'_y':xy[i][j][1],side+'_confidence':conf[i][j]})
    foot=select_foot(row,threshold=.5,width=896,height=672)
    if foot is None:continue
    world=project_pixel(sensor,transform,foot[:2],bounds)
    if world is not None:predictions.append({'id':i,'x':world[0],'y':world[1],'box':box,'confidence':score,'foot_pixel':list(foot[:2])})
   pairs=unique_position_pairs(predictions,refs[frame],.5);lookup={p['id']:p for p in predictions}
   for pair in pairs:pair.update(box=lookup[pair['prediction_id']]['box'],confidence=lookup[pair['prediction_id']]['confidence'],foot_pixel=lookup[pair['prediction_id']]['foot_pixel'])
   rows.append({'frame':frame,'predictions':predictions,'weak_pairs':pairs,'reference_count':len(refs[frame]),'raw_detections':len(boxes),'duplicates_excluded':len(duplicate)})
   total_pred+=len(boxes);total_valid+=len(predictions);total_pairs+=len(pairs)
 finally:cap.release()
 torch.cuda.synchronize();tmp=dest.with_suffix('.jsonl.tmp')
 with tmp.open('w') as f:
  for row in rows:f.write(json.dumps(row,allow_nan=False)+'\n')
 os.replace(tmp,dest);result={'contract':contract,'artifacts':{dest.name:sha256(dest)},'scope':'unique position proximity proxies only; not independently verified person identity','raw_detections':total_pred,'geometry_valid':total_valid,'weak_pairs':total_pairs};tmp=cache.with_suffix('.json.tmp');tmp.write_text(json.dumps(result,indent=2));os.replace(tmp,cache);print(camera,'detections',total_pred,'valid',total_valid,'weak pairs',total_pairs,flush=True)
