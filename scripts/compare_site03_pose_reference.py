"""Paired experimental box-vs-ankle projections on fixed reference-proxy samples."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,math,subprocess,sys
import cv2,numpy as np
from scipy.spatial.transform import Rotation
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.pose_foot import select_foot
from walkflows.reference_eval import convert_reference
raw=root/'data/raw/multiview/006_site03_tracks';assets=root/'data/upstream-research';pose=root/'data/processed/site03-pose-evidence';floor=root/'data/processed/site03-floor-probe';refdir=root/'data/processed/site03-reference-eval';out=root/'data/processed/site03-pose-comparison';out.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
scene=json.loads((assets/'site03_scene03.json').read_text());pose_summary=json.loads((pose/'summary.json').read_text());floor_summary=json.loads((floor/'summary.json').read_text());reference_summary=json.loads((refdir/'summary.json').read_text());gt=convert_reference(json.loads((raw/'ground-truth.json').read_text())['track_results'])['by_frame']
if sha(refdir/'candidate_matches.csv')!=reference_summary['candidate_matches_sha256'] or sha(raw/'ground-truth.json')!=reference_summary['source_sha256']:raise ValueError('reference input mismatch')
match={}
with (refdir/'candidate_matches.csv').open() as f:
 for r in csv.DictReader(f):
  if float(r['threshold']) in (.5,1.) and r['multiple_reference_candidates']=='False':match[(r['camera'],int(r['frame']),int(r['local_id']),float(r['threshold']))]=r
reports=[];output=[]
for entry,projection in zip(pose_summary['cameras'],floor_summary['cameras'],strict=True):
 camera=entry['camera'];posepath=pose/(camera+'_track_pose.csv');floorpath=floor/(camera+'_experimental_floor.csv')
 if camera!=projection['camera'] or entry['track_sha256']!=projection['source_sha256'] or sha(posepath)!=entry['pose_csv_sha256'] or sha(floorpath)!=projection['projection_sha256']:raise ValueError('pose/projection provenance mismatch '+camera)
 with posepath.open() as f:poses=list(csv.DictReader(f))
 with floorpath.open() as f:floors=list(csv.DictReader(f))
 pm={(int(r['frame']),int(r['local_id'])):r for r in poses};fm={(int(r['frame']),int(r['local_id'])):r for r in floors}
 if len(pm)!=len(poses) or len(fm)!=len(floors) or set(pm)!=set(fm):raise ValueError('pose/floor key mismatch')
 sensor=json.loads((assets/(camera+'.json')).read_text())['sensor0'];i=scene['bcam-keys'].index(camera);et=scene['bcam-transforms'][i];C=np.array(et['translation']);rot=Rotation.from_quat(et['rotation']);scale=np.array(sensor['format'])/[896,672];hull=np.asarray(sensor['calib-hull'],dtype=np.float32);bounds=scene['hist-aabb'];reports_for_cam=[]
 for confidence in (.25,.5,.75):
  feet=[]
  for key,row in pm.items():
   foot=select_foot(row,threshold=confidence,width=896,height=672)
   if foot:feet.append((key,foot))
  projected={}
  if feet:
   pixels=np.array([[foot[0],foot[1]] for _,foot in feet]);conditioned=(pixels*scale-np.array(sensor['center']))*sensor['scale'];binary=root/'data/processed/site02-native-lift/lift-probe'
   result=subprocess.check_output([str(binary)],input=''.join(f'{x:.17g} {y:.17g}\n' for x,y in conditioned),text=True);terms=np.array([[float(v) for v in line.split()] for line in result.splitlines()]);uv=terms@np.asarray(sensor['A']).T;rays=rot.apply(np.column_stack([uv,np.ones(len(uv))]))
   with np.errstate(divide='ignore',invalid='ignore'):distance=-C[2]/rays[:,2];world=C+distance[:,None]*rays
   for j,(key,foot) in enumerate(feet):
    valid=bool(cv2.pointPolygonTest(hull,tuple(pixels[j]*scale),False)>=0 and np.isfinite(world[j]).all() and np.isfinite(distance[j]) and distance[j]>0 and abs(rays[j,2])>1e-8 and bounds[0]<=world[j,0]<=bounds[2] and bounds[1]<=world[j,1]<=bounds[3])
    projected[key]=(foot,world[j,:2],valid)
  variants=[]
  for gate in (.5,1.):
   comparisons=[];proxy_count=0;pose_available=0;pose_geometry_valid=0
   for key,base in fm.items():
    proxy=match.get((camera,key[0],key[1],gate))
    if not proxy:continue
    proxy_count+=1
    if key not in projected:continue
    pose_available+=1;foot,position,valid=projected[key]
    if not valid:continue
    pose_geometry_valid+=1;refs=[r for r in gt[key[0]] if r['id']==int(proxy['reference_id'])]
    if len(refs)!=1:raise ValueError('reference id missing or duplicate')
    ref=refs[0];box_distance=math.hypot(float(base['experimental_x'])-ref['x'],float(base['experimental_y'])-ref['y']);foot_distance=math.hypot(position[0]-ref['x'],position[1]-ref['y']);delta=foot_distance-box_distance
    comparison={'camera':camera,'frame':key[0],'local_id':key[1],'reference_id':ref['id'],'reference_gate':gate,'confidence_threshold':confidence,'selected_ankles':foot[2],'foot_pixel_x':foot[0],'foot_pixel_y':foot[1],'box_world_x':float(base['experimental_x']),'box_world_y':float(base['experimental_y']),'foot_world_x':float(position[0]),'foot_world_y':float(position[1]),'box_reference_distance':box_distance,'foot_reference_distance':foot_distance,'delta_foot_minus_box':delta};comparisons.append(comparison);output.append(comparison)
   delta=[x['delta_foot_minus_box'] for x in comparisons];variants.append({'reference_proxy_gate':gate,'proxy_eligible':proxy_count,'pose_point_available':pose_available,'pose_geometry_valid_paired':pose_geometry_valid,'median_box_distance':float(np.median([x['box_reference_distance'] for x in comparisons])) if comparisons else None,'median_foot_distance':float(np.median([x['foot_reference_distance'] for x in comparisons])) if comparisons else None,'median_paired_delta':float(np.median(delta)) if delta else None,'foot_closer':sum(x< -1e-9 for x in delta),'box_closer':sum(x>1e-9 for x in delta),'ties':sum(abs(x)<=1e-9 for x in delta)})
  reports_for_cam.append({'confidence_threshold':confidence,'all_track_observations':len(pm),'pose_point_available':len(feet),'pose_point_geometry_valid':sum(v[2] for v in projected.values()),'variants':variants})
 reports.append({'camera':camera,'pose_status_counts':entry['status_counts'],'results':reports_for_cam})
fields=['camera','frame','local_id','reference_id','reference_gate','confidence_threshold','selected_ankles','foot_pixel_x','foot_pixel_y','box_world_x','box_world_y','foot_world_x','foot_world_y','box_reference_distance','foot_reference_distance','delta_foot_minus_box']
with (out/'paired.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(output)
report={'scope':'Conditional paired geometry comparison, NOT physical accuracy, ground truth identity, visibility, or validated improvement.','selection_bias':'Reference proxy assignment is chosen using box projection; box distance is truncated by proxy gate. Comparisons are restricted to unique reference proximity, unique pose box overlap, valid pose and geometry.','pose_score_thresholds':[.25,.5,.75],'proxy_distance_gates':[.5,1.0],'data':reports,'inputs':{'pose_summary_sha256':sha(pose/'summary.json'),'reference_summary_sha256':sha(refdir/'summary.json'),'floor_summary_sha256':sha(floor/'summary.json')},'paired_sha256':sha(out/'paired.csv')}
(out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
