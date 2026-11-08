"""Paired YOLO11n/s pose comparison on fixed tracks, not accuracy validation."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,math,subprocess,sys
import cv2,numpy as np
from scipy.spatial.transform import Rotation
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.pose_foot import select_foot
from walkflows.paired_pose_comparison import summarize_pairs
from walkflows.reference_eval import convert_reference
p=root/'data/processed';assets=root/'data/upstream-research';raw=root/'data/raw/multiview/006_site03_tracks';ns=p/'site03-pose-evidence';ss=p/'site03-pose-s-evidence';refdir=p/'site03-reference-eval';out=p/'site03-pose-model-comparison';out.mkdir(parents=True,exist_ok=True)
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
nmeta=json.loads((ns/'summary.json').read_text());smeta=json.loads((ss/'summary.json').read_text());rmeta=json.loads((refdir/'summary.json').read_text());gt=convert_reference(json.loads((raw/'ground-truth.json').read_text())['track_results'])['by_frame'];scene=json.loads((assets/'site03_scene03.json').read_text())
if sha(refdir/'candidate_matches.csv')!=rmeta['candidate_matches_sha256'] or sha(raw/'ground-truth.json')!=rmeta['source_sha256']:raise ValueError('reference mismatch')
if nmeta['weight_sha256']!='869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0' or smeta['weight_sha256']!='1060bda4a27012060eca246f9b2adeea22eabb045a1e58f8d229be29b7ebc2ba':raise ValueError('unexpected model weights')
if any(nmeta[k]!=smeta[k] for k in ('opencv','ultralytics','torch','conf','imgsz','iou_threshold')):raise ValueError('incomparable inference settings')
if sha(root/'data/models/yolo11n-pose.pt')!=nmeta['weight_sha256'] or sha(root/'data/models/yolo11s-pose.pt')!=smeta['weight_sha256']:raise ValueError('weight file mismatch')
floor_meta=json.loads((p/'site03-floor-probe/summary.json').read_text())
if sha(assets/'site03_scene03.json')!=floor_meta['scene_sha256'] or sha(p/'site02-native-lift/lift-probe')!=floor_meta['native_lift_binary_sha256']:raise ValueError('geometry provenance mismatch')
for entry in floor_meta['cameras']:
 if entry['camera'] in ('C0001055_v4','C0001056_v2') and sha(assets/(entry['camera']+'.json'))!=entry['calibration_sha256']:raise ValueError('camera calibration mismatch')

proxy={}
with (refdir/'candidate_matches.csv').open() as f:
 for r in csv.DictReader(f):
  if float(r['threshold']) in (.5,1.) and r['multiple_reference_candidates']=='False':proxy[(r['camera'],int(r['frame']),int(r['local_id']),float(r['threshold']))]=int(r['reference_id'])
reports=[];output=[]
for camera in ('C0001055_v4','C0001056_v2'):
 maps=[]
 for directory,meta in ((ns,nmeta),(ss,smeta)):
  entry=next(x for x in meta['cameras'] if x['camera']==camera);path=directory/(camera+'_track_pose.csv')
  if sha(path)!=entry['pose_csv_sha256']:raise ValueError('pose hash mismatch')
  with path.open() as f:rows=list(csv.DictReader(f))
  d={(int(r['frame']),int(r['local_id'])):r for r in rows}
  if len(d)!=len(rows):raise ValueError('duplicate keys')
  maps.append((entry,d))
 if maps[0][0]['track_sha256']!=maps[1][0]['track_sha256'] or set(maps[0][1])!=set(maps[1][1]):raise ValueError('track support mismatch')
 sensor=json.loads((assets/(camera+'.json')).read_text())['sensor0'];i=scene['bcam-keys'].index(camera);et=scene['bcam-transforms'][i];C=np.array(et['translation']);rot=Rotation.from_quat(et['rotation']);scale=np.array(sensor['format'])/[896,672];hull=np.asarray(sensor['calib-hull'],dtype=np.float32);bounds=scene['hist-aabb'];projected=[];counts=[]
 for entry,data in maps:
  feet=[(key,foot) for key,row in data.items() if (foot:=select_foot(row,threshold=.5,width=896,height=672))];counts.append({'track_observations':len(data),'unique_pose_matches':sum(r['status']=='unique' for r in data.values()),'usable_ankles':len(feet)})
  if not feet:projected.append({});continue
  pixels=np.array([[foot[0],foot[1]] for _,foot in feet]);conditioned=(pixels*scale-np.array(sensor['center']))*sensor['scale'];binary=p/'site02-native-lift/lift-probe';result=subprocess.check_output([str(binary)],input=''.join(f'{x:.17g} {y:.17g}\n' for x,y in conditioned),text=True);terms=np.array([[float(v) for v in line.split()] for line in result.splitlines()]);rays=rot.apply(np.column_stack([terms@np.asarray(sensor['A']).T,np.ones(len(terms))]))
  with np.errstate(divide='ignore',invalid='ignore'):dist=-C[2]/rays[:,2];world=C+dist[:,None]*rays
  selected={}
  for j,(key,foot) in enumerate(feet):
   if cv2.pointPolygonTest(hull,tuple(pixels[j]*scale),False)>=0 and np.isfinite(world[j]).all() and np.isfinite(dist[j]) and dist[j]>0 and abs(rays[j,2])>1e-8 and bounds[0]<=world[j,0]<=bounds[2] and bounds[1]<=world[j,1]<=bounds[3]:selected[key]=(float(world[j,0]),float(world[j,1]))
  counts[-1]['valid_projected_ankles']=len(selected);projected.append(selected)
 variants=[]
 for gate in (.5,1.):
  pairs=[]
  for key in sorted(set(projected[0])&set(projected[1])):
   rid=proxy.get((camera,key[0],key[1],gate))
   if rid is None:continue
   refs=[r for r in gt[key[0]] if r['id']==rid]
   if len(refs)!=1:raise ValueError('reference identity mismatch')
   ref=refs[0];n=math.hypot(projected[0][key][0]-ref['x'],projected[0][key][1]-ref['y']);s=math.hypot(projected[1][key][0]-ref['x'],projected[1][key][1]-ref['y']);pairs.append((n,s));output.append({'camera':camera,'frame':key[0],'local_id':key[1],'proxy_gate':gate,'reference_id':rid,'nano_distance':n,'small_distance':s})
  variants.append({'proxy_gate':gate,**summarize_pairs(pairs)})
 reports.append({'camera':camera,'nano':counts[0],'small':counts[1],'variants':variants})
fields=['camera','frame','local_id','proxy_gate','reference_id','nano_distance','small_distance']
with (out/'paired.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(output)
result={'scope':'Conditional paired reference-proximity comparison, not independently validated localization, identity or business accuracy.','bias':'Reference assignment uses box-bottom proxy and shared valid pose/geometry; frames are correlated; no visibility ground truth.','models':{'nano_sha256':nmeta['weight_sha256'],'small_sha256':smeta['weight_sha256']},'inputs':{'nano_summary_sha256':sha(ns/'summary.json'),'small_summary_sha256':sha(ss/'summary.json'),'reference_summary_sha256':sha(refdir/'summary.json')},'paired_sha256':sha(out/'paired.csv'),'cameras':reports};(out/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
