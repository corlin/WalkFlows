"""Export per-observation experimental pose-foot projections; never promote to strict."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,math,subprocess,sys
import cv2,numpy as np
from scipy.spatial.transform import Rotation
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.pose_foot import select_foot
from walkflows.crossview import local_duplicate_keys
assets=root/'data/upstream-research';pose=root/'data/processed/site03-pose-evidence';floor=root/'data/processed/site03-floor-probe';tracking=root/'data/processed/site03-gpu-conf010';out=root/'data/processed/site03-pose-floor';out.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
scene_path=assets/'site03_scene03.json';scene=json.loads(scene_path.read_text());summary=json.loads((pose/'summary.json').read_text());floor_summary=json.loads((floor/'summary.json').read_text());binary=root/'data/processed/site02-native-lift/lift-probe'
if sha(scene_path)!=floor_summary['scene_sha256'] or sha(binary)!=floor_summary['native_lift_binary_sha256']:raise ValueError('geometry source mismatch')
fields=['frame','local_id','pose_status','foot_kind','foot_x','foot_y','floor_x','floor_y','research_candidate','exclusion_reasons'];reports=[]
for entry,geometry in zip(summary['cameras'],floor_summary['cameras'],strict=True):
 camera=entry['camera'];posepath=pose/(camera+'_track_pose.csv');trackpath=tracking/(camera+'_observations.csv');sensorpath=assets/(camera+'.json')
 if camera!=geometry['camera'] or sha(posepath)!=entry['pose_csv_sha256'] or sha(trackpath)!=entry['track_sha256'] or sha(sensorpath)!=geometry['calibration_sha256']:raise ValueError('input provenance mismatch '+camera)
 with posepath.open() as f:poses=list(csv.DictReader(f))
 with trackpath.open() as f:tracks=list(csv.DictReader(f))
 pm={(int(r['frame']),int(r['local_id'])):r for r in poses};tm={(int(r['frame']),int(r['local_id'])):r for r in tracks}
 if len(pm)!=len(poses) or len(tm)!=len(tracks) or set(pm)!=set(tm):raise ValueError('observation key mismatch')
 dup=local_duplicate_keys([{'frame':k[0],'id':k[1],'box':tuple(float(r[x]) for x in ('left','top','right','bottom'))} for k,r in tm.items()],containment=.9)
 chosen={k:select_foot(row,threshold=.5,width=896,height=672) for k,row in pm.items()};feet=[(k,v) for k,v in chosen.items() if v];results={}
 if feet:
  sensor=json.loads(sensorpath.read_text())['sensor0'];et=scene['bcam-transforms'][scene['bcam-keys'].index(camera)];scale=np.array(sensor['format'])/[896,672];pixels=np.array([[foot[0],foot[1]] for _,foot in feet]);conditioned=(pixels*scale-np.array(sensor['center']))*sensor['scale'];text=subprocess.check_output([str(binary)],input=''.join(f'{x:.17g} {y:.17g}\n' for x,y in conditioned),text=True);terms=np.array([[float(v) for v in line.split()] for line in text.splitlines()]);uv=terms@np.asarray(sensor['A']).T;rays=Rotation.from_quat(et['rotation']).apply(np.column_stack([uv,np.ones(len(uv))]));C=np.array(et['translation']);hull=np.asarray(sensor['calib-hull'],dtype=np.float32);bounds=scene['hist-aabb']
  with np.errstate(divide='ignore',invalid='ignore'):distance=-C[2]/rays[:,2];world=C+distance[:,None]*rays
  for i,(key,foot) in enumerate(feet):
   reasons=[];finite=bool(np.isfinite(world[i]).all())
   if cv2.pointPolygonTest(hull,tuple(pixels[i]*scale),False)<0:reasons.append('outside_calibration_hull')
   if not np.isfinite(distance[i]) or distance[i]<=0 or abs(rays[i,2])<=1e-8:reasons.append('invalid_ray')
   if not finite or not (bounds[0]<=world[i,0]<=bounds[2] and bounds[1]<=world[i,1]<=bounds[3]):reasons.append('outside_scene_bounds')
   results[key]=(foot,world[i,:2] if finite else None,reasons)
 rows=[]
 for key,pose_row in pm.items():
  reasons=[];foot='';x=y='';fx=fy='';kind=''
  if key in dup:reasons.append('local_duplicate_candidate')
  if not chosen[key]:reasons.append('pose_foot_unavailable')
  else:
   foot,xy,geometry_reasons=results[key];kind=foot[2];fx,fy=foot[:2];reasons.extend(geometry_reasons)
   if xy is not None:x,y=map(float,xy)
  rows.append({'frame':key[0],'local_id':key[1],'pose_status':pose_row['status'],'foot_kind':kind,'foot_x':fx,'foot_y':fy,'floor_x':x,'floor_y':y,'research_candidate':int(not reasons),'exclusion_reasons':'|'.join(reasons)})
 path=out/(camera+'_pose_floor.csv')
 with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 reports.append({'camera':camera,'observations':len(rows),'research_candidates':sum(r['research_candidate'] for r in rows),'exclusion_counts':dict(Counter(reason for row in rows for reason in row['exclusion_reasons'].split('|') if reason)),'output_sha256':sha(path),'pose_csv_sha256':entry['pose_csv_sha256'],'track_csv_sha256':entry['track_sha256'],'calibration_sha256':geometry['calibration_sha256']})
result={'scope':'Experimental pose-foot projections only; no strict quality gate, identity or business metric.','pose_score_threshold':.5,'one_ankle_policy':'midpoint if both qualify, otherwise qualified single ankle','pose_confidence':'uncalibrated; not validated visibility','duplicate_containment':.9,'scene_sha256':sha(scene_path),'native_lift_sha256':sha(binary),'cameras':reports}
(out/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
