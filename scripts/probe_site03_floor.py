"""Map site03 camera-local box bottoms through pinned native lift; experimental only."""
from pathlib import Path
import csv,hashlib,json,subprocess,sys
import cv2,numpy as np
from scipy.spatial.transform import Rotation
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from fetch_site03_calibration import files,valid
assets=root/'data/upstream-research';scene_path=assets/'site03_scene03.json'
if not valid(scene_path,files['scenes/site03_scene03.json']):raise ValueError('scene checksum mismatch')
scene=json.loads(scene_path.read_text());
if scene['global-transformation']!={'translation':[0,0,0],'rotation':[0,0,0,1],'scale':1.0}:raise ValueError('nonidentity global transform unsupported')
out=root/'data/processed/site03-floor-probe';out.mkdir(parents=True,exist_ok=True);binary=root/'data/processed/site02-native-lift/lift-probe'
if not binary.is_file():raise RuntimeError('Run scripts/probe_native_lift.py first')
summary={'scope':'Experimental image box-bottom projection; not physical ground truth, person identity, or validated cross-camera fusion.','scene_sha256':hashlib.sha256(scene_path.read_bytes()).hexdigest(),'native_lift_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'native_lift_header_sha256':hashlib.sha256((assets/'calibration-utils.hpp').read_bytes()).hexdigest(),'cameras':[]}
for camera,et in zip(scene['bcam-keys'],scene['bcam-transforms'],strict=True):
 source=root/'data/processed/site03-gpu-conf010'/(camera+'_observations.csv');run=root/'data/processed/site03-gpu-conf010'/(camera+'_run.json')
 if not source.exists() or not run.exists():summary['cameras'].append({'camera':camera,'status':'missing tracking output'});continue
 meta=json.loads(run.read_text())
 if hashlib.sha256(source.read_bytes()).hexdigest()!=meta['observations_sha256']:raise ValueError('tracking checksum mismatch '+camera)
 sensor_path=assets/(camera+'.json')
 if not valid(sensor_path,files['binocular/'+camera+'.json']):raise ValueError('calibration checksum mismatch '+camera)
 sensor=json.loads(sensor_path.read_text())['sensor0']
 with source.open() as f:obs=list(csv.DictReader(f))
 rows=[]
 if obs:
  pixels=np.array([[(float(o['left'])+float(o['right']))/2,float(o['bottom'])] for o in obs]);scale=np.array(sensor['format'])/[896,672];C=np.array(et['translation']);q=np.array(et['rotation']);assert abs(np.linalg.norm(q)-1)<1e-6 and et['scale']==1
  conditioned=(pixels*scale-np.array(sensor['center']))*sensor['scale']
  output=subprocess.check_output([str(binary)],input=''.join(f'{x:.17g} {y:.17g}\n' for x,y in conditioned),text=True)
  terms=np.array([[float(v) for v in line.split()] for line in output.splitlines()]);uv=terms@np.asarray(sensor['A']).T;local=np.column_stack([uv,np.ones(len(uv))]);rays=Rotation.from_quat(q).apply(local)
  with np.errstate(divide='ignore',invalid='ignore'):t=-C[2]/rays[:,2];world=C+t[:,None]*rays
  hull=np.asarray(sensor['calib-hull'],dtype=np.float32);bounds=scene['hist-aabb']
  for i,o in enumerate(obs):
   inside=cv2.pointPolygonTest(hull,tuple(pixels[i]*scale),False)>=0;finite=bool(np.isfinite(world[i]).all());forward=bool(np.isfinite(t[i]) and t[i]>0 and abs(rays[i,2])>1e-8);in_scene=bool(finite and bounds[0]<=world[i,0]<=bounds[2] and bounds[1]<=world[i,1]<=bounds[3])
   rows.append([int(o['frame']),int(o['local_id']),*pixels[i],*world[i],int(inside),int(forward),int(in_scene)])
 dest=out/(camera+'_experimental_floor.csv')
 with dest.open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['frame','local_id','pixel_x','pixel_y','experimental_x','experimental_y','experimental_z','inside_calibration_hull','forward_nonparallel','in_scene_bounds']);w.writerows(rows)
 summary['cameras'].append({'camera':camera,'status':'complete','observations':len(rows),'all_geometry_gates':sum(row[7] and row[8] and row[9] for row in rows),'source_sha256':meta['observations_sha256'],'projection_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'calibration_sha256':hashlib.sha256(sensor_path.read_bytes()).hexdigest()})
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
