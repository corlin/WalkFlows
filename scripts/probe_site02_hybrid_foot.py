"""Site02 pose-first/box-fallback research observations on existing evidence."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,subprocess,sys
import cv2,numpy as np
from scipy.spatial.transform import Rotation
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.foot_policy import select_location
from walkflows.pose_foot import select_foot
processed=root/'data/processed';assets=root/'data/upstream-research';quality=processed/'site02-quality/observations.jsonl';poses=processed/'site02-pose-full';out=processed/'site02-hybrid-foot';out.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();scene=json.loads((assets/'site02_scene01_v1.json').read_text());pose_summary=json.loads((poses/'summary.json').read_text());records=[json.loads(x) for x in quality.read_text().splitlines()];output=[];reports=[]
for info in pose_summary['cameras']:
 camera=info['camera'];posepath=poses/(camera+'_track_pose.csv');track=processed/'site02-gpu-conf010'/(camera+'_observations.csv');sensorpath=assets/(camera+'.json');
 if sha(track)!=info['track_csv_sha256']:raise ValueError('track provenance mismatch')
 with posepath.open() as f:pr=list(csv.DictReader(f))
 pm={(int(r['frame']),int(r['local_id'])):r for r in pr};qm={(r['frame'],r['local_id']):r for r in records if r['camera']==camera}
 if len(pm)!=len(pr) or len(qm)!=sum(r['camera']==camera for r in records) or set(pm)!=set(qm):raise ValueError('key mismatch '+camera)
 chosen={}
 for key,row in pm.items():
  norm={'status':row['match_status']}
  for side in ('left','right'):
   for f in ('x','y','confidence'):norm[side+'_'+f]=row[side+'_ankle_'+f]
  point=select_foot(norm,threshold=.5,width=896,height=672)
  if point:chosen[key]=point
 sensor=json.loads(sensorpath.read_text())['sensor0'];et=scene['bcam-transforms'][scene['bcam-keys'].index(camera)];scale=np.array(sensor['format'])/[896,672];C=np.array(et['translation']);hull=np.asarray(sensor['calib-hull'],dtype=np.float32);bounds=scene['hist-aabb'];projected={};pose_reasons={}
 if chosen:
  entries=list(chosen.items());pixels=np.array([[v[0],v[1]] for _,v in entries]);conditioned=(pixels*scale-np.array(sensor['center']))*sensor['scale'];binary=processed/'site02-native-lift/lift-probe';res=subprocess.check_output([str(binary)],input=''.join(f'{x:.17g} {y:.17g}\n' for x,y in conditioned),text=True);terms=np.array([[float(v) for v in line.split()] for line in res.splitlines()]);uv=terms@np.asarray(sensor['A']).T;rays=Rotation.from_quat(et['rotation']).apply(np.column_stack([uv,np.ones(len(uv))]))
  with np.errstate(divide='ignore',invalid='ignore'):distance=-C[2]/rays[:,2];world=C+distance[:,None]*rays
  for i,(key,foot) in enumerate(entries):
   reasons=[];finite=bool(np.isfinite(world[i]).all())
   if cv2.pointPolygonTest(hull,tuple(pixels[i]*scale),False)<0:reasons.append('outside_calibration_hull')
   if not np.isfinite(distance[i]) or distance[i]<=0 or abs(rays[i,2])<=1e-8:reasons.append('invalid_ray')
   if not finite or not (bounds[0]<=world[i,0]<=bounds[2] and bounds[1]<=world[i,1]<=bounds[3]):reasons.append('outside_scene_bounds')
   pose_reasons[key]=reasons;projected[key]=({'x':float(world[i,0]),'y':float(world[i,1]),'valid':True} if not reasons else None)
 current=[]
 for key,q in qm.items():
  qv=q['quality'];valid=qv['inside_hull'] is True and qv['in_scene'] is True and qv['forward_ray'] is True
  box={'x':q['xy'][0] if valid else None,'y':q['xy'][1] if valid else None,'valid':valid};result=select_location(box,projected.get(key),duplicate=qv['duplicate_candidate'],max_disagreement=.75)
  row={'camera':camera,'frame':key[0],'local_id':key[1],**result,'box_geometry_valid':valid,'pose_geometry_candidate':projected.get(key) is not None,'pose_match_status':pm[key]['match_status'],'pose_foot_kind':chosen[key][2] if key in chosen else None,'pose_pixel':list(chosen[key][:2]) if key in chosen else None,'pose_exclusion_reasons':pose_reasons.get(key,[]) if key in chosen else ['pose_foot_unavailable'],'original_quality_reasons':q['reasons'],'strict_candidate':False};current.append(row);output.append(row)
 reports.append({'camera':camera,'observations':len(current),'methods':dict(Counter(x['method'] for x in current)),'strict_candidates':0,'pose_sha256':sha(posepath),'tracking_sha256':sha(track),'calibration_sha256':sha(sensorpath)})
path=out/'observations.jsonl'
with path.open('w') as f:
 for row in output:f.write(json.dumps(row,allow_nan=False)+'\n')
report={'scope':'Research-only pose-first or box fallback; unvalidated floor, visibility, sync, identity.','max_disagreement':.75,'pose_score_threshold':.5,'quality_sha256':sha(quality),'pose_summary_sha256':sha(poses/'summary.json'),'observations_sha256':sha(path),'cameras':reports}
(out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
