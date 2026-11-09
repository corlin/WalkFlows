"""Load optional direct-pose hypotheses only when provenance is current."""
from pathlib import Path
import csv,json,math
from walkflows.artifact_cache import sha256

def load_direct_pose(root,baseline_hypothesis_sha,reference_sha,scene_sha,*,all_cameras=False):
 root=Path(root);processed=root/'data/processed';folder=processed/('site03-direct-pose-all-journeys' if all_cameras else 'site03-direct-pose-journeys');report_path=folder/'report.json';hyp_path=folder/'hypotheses.json'
 if not report_path.exists() and not hyp_path.exists():return None
 try:
  report=json.loads(report_path.read_text());hyp=json.loads(hyp_path.read_text())
  if report['hypotheses_sha256']!=sha256(hyp_path) or report['baseline_hypotheses_sha256']!=baseline_hypothesis_sha or report['reference_sha256']!=reference_sha or report['script_sha256']!=sha256(root/'scripts/evaluate_site03_direct_pose_journeys.py') or hyp['inputs']!=report['inputs']:return None
  base_meta=json.loads((processed/'site03-pose-floor/summary.json').read_text());entries={x['camera']:x for x in base_meta['cameras']}
  if base_meta['scene_sha256']!=scene_sha or set(report['inputs'])!=set(entries):return None
  if all_cameras and (len(base_meta['cameras'])!=6 or set(entries)!={'C0001020_v1','C0001025_v1','C0001029_v2','C0001053_v5','C0001055_v4','C0001056_v2'} or any(item['kind']!='direct_pose' for item in report['inputs'].values())):return None
  camera_boxes={}
  for cam,item in report['inputs'].items():
   if item['kind']=='baseline':
    path=processed/'site03-pose-floor'/(cam+'_pose_floor.csv')
    if item['observations_sha256']!=entries[cam]['output_sha256'] or sha256(path)!=item['observations_sha256']:return None
   elif item['kind']=='direct_pose':
    folder2=processed/'site03-direct-pose-probe'/cam;info_path=folder2/'report.json';obs=folder2/'observations.csv';info=json.loads(info_path.read_text())
    if sha256(info_path)!=item['report_sha256'] or sha256(obs)!=item['observations_sha256'] or info['observations_sha256']!=item['observations_sha256'] or info['camera']!=cam or info['scene_sha256']!=scene_sha or info['reference_sha256']!=reference_sha or info['script_sha256']!=sha256(root/'scripts/probe_site03_pose_direct.py'):return None
    if info['weights_sha256']!=sha256(root/'data/models/yolo11s-pose.pt') or info['video_sha256']!=sha256(root/'data/raw/multiview/006_site03_tracks'/(cam+'.mp4')) or info['sensor_sha256']!=sha256(root/'data/upstream-research'/(cam+'.json')):return None
    with obs.open(newline='') as f: rows=list(csv.DictReader(f))
    boxes=[];seen=set()
    for row in rows:
     frame=int(row['frame']);ident=int(row['local_id']);box=[float(row[k]) for k in ('left','top','right','bottom')]
     if not 0<=frame<400 or ident<0 or (frame,ident) in seen or not all(math.isfinite(x) for x in box) or box[0]>=box[2] or box[1]>=box[3]:return None
     seen.add((frame,ident));boxes.append({'frame':frame,'id':ident,'box':box})
    camera_boxes[cam]=boxes
   else:return None
  if not isinstance(hyp['hypotheses'],list):return None
  return {'hypotheses':hyp['hypotheses'],'camera_boxes':camera_boxes,'sha256':report['hypotheses_sha256']}
 except (OSError,ValueError,KeyError,TypeError):return None
