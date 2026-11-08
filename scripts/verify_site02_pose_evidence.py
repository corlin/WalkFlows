"""Verify existing site02 pose evidence against model, videos, tracks and frame ledgers."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,sys
root=Path(__file__).resolve().parents[1];processed=root/'data/processed';folder=processed/'site02-pose-full';raw=root/'data/raw/multiview/002_site02_gaze';summary=json.loads((folder/'summary.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(root/'data/models/yolo11n-pose.pt')!=summary['weights_sha256'] or sha(root/'scripts/probe_site02_pose.py')!=summary['script_sha256']:raise ValueError('pose weights or script mismatch')
quality=[json.loads(x) for x in (processed/'site02-quality/observations.jsonl').read_text().splitlines()];expected={'C0001001_v10','C0001011_v10'}
if {x['camera'] for x in summary['cameras']}!=expected or len(summary['cameras'])!=2:raise ValueError('camera mismatch')
for item in summary['cameras']:
 cam=item['camera'];track=processed/'site02-gpu-conf010'/(cam+'_observations.csv');video=raw/(cam+'.mp4')
 if sha(track)!=item['track_csv_sha256'] or sha(video)!=item['video_sha256']:raise ValueError('source checksum mismatch')
 def read(path):
  with path.open() as f:return list(csv.DictReader(f))
 rows=read(folder/(cam+'_track_pose.csv'));frames=read(folder/(cam+'_frames.csv'));boxes=read(folder/(cam+'_pose_boxes.csv'));tracks=read(track)
 key=lambda r:(int(r['frame']),int(r['local_id']));keys={key(r) for r in rows};qkeys={(r['frame'],r['local_id']) for r in quality if r['camera']==cam}
 if len(rows)!=len(keys) or keys!={key(r) for r in tracks} or keys!=qkeys or len(rows)!=item['track_observations'] or dict(Counter(r['match_status'] for r in rows))!=item['match_status']:raise ValueError('observation coverage mismatch '+cam)
 if len(frames)!=218 or [int(x['frame']) for x in frames]!=list(range(218)):raise ValueError('frame coverage mismatch')
 boxes_by_key={(int(x['frame']),int(x['pose_index'])) for x in boxes};unique=[(int(x['frame']),int(x['pose_index'])) for x in rows if x['match_status']=='unique']
 if len(boxes_by_key)!=len(boxes) or len(unique)!=len(set(unique)) or not set(unique)<=boxes_by_key:raise ValueError('pose index mismatch')
 if sum(int(r['pose_boxes']) for r in frames)!=len(boxes) or sum(int(r['track_observations']) for r in frames)!=len(rows) or sum(int(r['unique_matches']) for r in frames)!=len(unique):raise ValueError('frame counts mismatch')
print('site02 pose evidence PASS',len(quality),'quality observations')
