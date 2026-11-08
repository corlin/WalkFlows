"""Cross-scene site02 pose-vs-box comparison, conditional on unique reference proximity."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,hashlib,json,math,subprocess,sys
import cv2,numpy as np
from scipy.spatial.transform import Rotation
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.pose_foot import select_foot
raw=root/'data/raw/multiview/002_site02_gaze';processed=root/'data/processed';assets=root/'data/upstream-research';quality=processed/'site02-quality/observations.jsonl';pose=processed/'site02-pose-full';reference=processed/'site02-reference-floor/reference_floor.csv';floor=processed/'site02-floor-probe';out=processed/'site02-pose-cross-scene';out.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
scene=json.loads((assets/'site02_scene01_v1.json').read_text());pose_summary=json.loads((pose/'summary.json').read_text());reference_summary=json.loads((reference.parent/'summary.json').read_text());original_gt=raw/'ground-truth.json'
if reference_summary['source_sha256']!=sha(original_gt):raise ValueError('reference provenance mismatch')
records=[json.loads(x) for x in quality.read_text().splitlines()];bycam=defaultdict(list)
for row in records:bycam[row['camera']].append(row)
with reference.open() as f:refs={int(r['clip_frame']):r for r in csv.DictReader(f)}
if len(refs)!=218 or set(refs)!=set(range(218)):raise ValueError('reference coverage mismatch')
reports=[];paired=[]
for info in pose_summary['cameras']:
 camera=info['camera'];track=processed/'site02-gpu-conf010'/(camera+'_observations.csv');posepath=pose/(camera+'_track_pose.csv');video=raw/(camera+'.mp4');sensorpath=assets/(camera+'.json')
 if sha(track)!=info['track_csv_sha256'] or sha(video)!=info['video_sha256']:raise ValueError('pose evidence provenance mismatch '+camera)
 with posepath.open() as f:poses=list(csv.DictReader(f))
 pm={(int(r['frame']),int(r['local_id'])):r for r in poses};qm={(r['frame'],r['local_id']):r for r in bycam[camera]}
 if len(pm)!=len(poses) or len(qm)!=len(bycam[camera]) or set(pm)!=set(qm):raise ValueError('pose quality keys mismatch')
 eligible=defaultdict(list)
 for key,q in qm.items():
  if q['status'] not in ('research_candidate_only','strict_candidate'):continue
  if q['source_sha256']!=info['video_sha256'] or q['raw_observation_artifact_sha256']!=info['track_csv_sha256']:raise ValueError('quality source mismatch')
  ref=refs[key[0]];distance=math.hypot(q['xy'][0]-float(ref['floor_x']),q['xy'][1]-float(ref['floor_y']))
  eligible[key[0]].append((key,distance))
 proxy={}
 for gate in (.5,1.):
  for frame,observations in eligible.items():
   near=[(key,d) for key,d in observations if d<=gate]
   if len(near)==1:proxy[(near[0][0],gate)]=near[0][1]
 sensor=json.loads(sensorpath.read_text())['sensor0'];et=scene['bcam-transforms'][scene['bcam-keys'].index(camera)];scale=np.array(sensor['format'])/[896,672];rot=Rotation.from_quat(et['rotation']);C=np.array(et['translation']);hull=np.asarray(sensor['calib-hull'],dtype=np.float32);bounds=scene['hist-aabb'];camera_stats=[]
 for conf in (.25,.5,.75):
  selected=[]
  for key,row in pm.items():
   normal={'status':row['match_status']}
   for side in ('left','right'):
    for field in ('x','y','confidence'):normal[side+'_'+field]=row[side+'_ankle_'+field]
   foot=select_foot(normal,threshold=conf,width=896,height=672)
   if foot:selected.append((key,foot))
  points={}
  if selected:
   pixels=np.array([[v[0],v[1]] for _,v in selected]);conditioned=(pixels*scale-np.array(sensor['center']))*sensor['scale'];binary=processed/'site02-native-lift/lift-probe';result=subprocess.check_output([str(binary)],input=''.join(f'{x:.17g} {y:.17g}\n' for x,y in conditioned),text=True);terms=np.array([[float(v) for v in line.split()] for line in result.splitlines()]);uv=terms@np.asarray(sensor['A']).T;rays=rot.apply(np.column_stack([uv,np.ones(len(uv))]))
   with np.errstate(divide='ignore',invalid='ignore'):dist=-C[2]/rays[:,2];world=C+dist[:,None]*rays
   for i,(key,foot) in enumerate(selected):
    valid=bool(cv2.pointPolygonTest(hull,tuple(pixels[i]*scale),False)>=0 and np.isfinite(world[i]).all() and np.isfinite(dist[i]) and dist[i]>0 and abs(rays[i,2])>1e-8 and bounds[0]<=world[i,0]<=bounds[2] and bounds[1]<=world[i,1]<=bounds[3]);points[key]=(foot,world[i,:2],valid)
  gates=[]
  for gate in (.5,1.):
   candidates=[key for (key,g),_ in proxy.items() if g==gate];complete=[]
   for key in candidates:
    if key not in points:continue
    foot,pos,valid=points[key]
    if not valid:continue
    ref=refs[key[0]];q=qm[key];error_box=proxy[(key,gate)];error_foot=math.hypot(pos[0]-float(ref['floor_x']),pos[1]-float(ref['floor_y']))
    row={'camera':camera,'frame':key[0],'local_id':key[1],'reference_gate':gate,'confidence_threshold':conf,'foot_kind':foot[2],'box_x':q['xy'][0],'box_y':q['xy'][1],'foot_x':float(pos[0]),'foot_y':float(pos[1]),'box_error':error_box,'foot_error':error_foot,'delta':error_foot-error_box};paired.append(row);complete.append(row)
   arr=[x['delta'] for x in complete];gates.append({'proxy_gate':gate,'unique_proxy_observations':len(candidates),'paired_observations':len(complete),'median_box_distance':float(np.median([r['box_error'] for r in complete])) if complete else None,'median_foot_distance':float(np.median([r['foot_error'] for r in complete])) if complete else None,'median_paired_delta':float(np.median(arr)) if arr else None,'foot_closer':sum(v < -1e-9 for v in arr),'box_closer':sum(v > 1e-9 for v in arr)})
  camera_stats.append({'score_threshold':conf,'pose_foot_available':len(points),'pose_foot_geometry_valid':sum(v[2] for v in points.values()),'gates':gates})
 reports.append({'camera':camera,'track_observations':len(qm),'pose_status':dict(Counter(x['match_status'] for x in poses)),'results':camera_stats,'inputs':{'pose_csv_sha256':sha(posepath),'quality_jsonl_sha256':sha(quality),'calibration_sha256':sha(sensorpath)}})
cross_camera=[]
for conf in (.25,.5,.75):
 for gate in (.5,1.):
  aligned=defaultdict(dict)
  for row in paired:
   if row['confidence_threshold']!=conf or row['reference_gate']!=gate:continue
   if row['camera'] in aligned[row['frame']]:raise ValueError('ambiguous camera-frame in paired support')
   aligned[row['frame']][row['camera']]=row
  common=[views for views in aligned.values() if len(views)==2]
  box=[math.hypot(v['C0001001_v10']['box_x']-v['C0001011_v10']['box_x'],v['C0001001_v10']['box_y']-v['C0001011_v10']['box_y']) for v in common]
  foot=[math.hypot(v['C0001001_v10']['foot_x']-v['C0001011_v10']['foot_x'],v['C0001001_v10']['foot_y']-v['C0001011_v10']['foot_y']) for v in common]
  cross_camera.append({'score_threshold':conf,'proxy_gate':gate,'common_frames':len(common),'median_box_pair_distance':float(np.median(box)) if box else None,'median_foot_pair_distance':float(np.median(foot)) if foot else None})
fields=['camera','frame','local_id','reference_gate','confidence_threshold','foot_kind','box_x','box_y','foot_x','foot_y','box_error','foot_error','delta']
with (out/'paired.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(paired)
report={'scope':'Site02 conditional reference-proximity comparison, not a blinded holdout; not validated physical accuracy or identity.','bias':'Reference selected by box position and frame, so samples are selected and box error truncated; not an independent identity label. Multiple candidate tracks within gate are excluded.','coverage':'Pose inferred only where a tracked box exists; absent pose is unknown.','reference_sha256':sha(reference),'quality_sha256':sha(quality),'pose_summary_sha256':sha(pose/'summary.json'),'paired_sha256':sha(out/'paired.csv'),'cross_camera_common_support':cross_camera,'cameras':reports}
(out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
