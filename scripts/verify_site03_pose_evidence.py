"""Validate cached pose evidence and its links to fixed site03 inputs."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'scripts'))
from fetch_site03_sample import FILES,valid
pose=root/'data/processed/site03-pose-evidence';tracking=root/'data/processed/site03-gpu-conf010';raw=root/'data/raw/multiview/006_site03_tracks';summary=json.loads((pose/'summary.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(root/'data/models/yolo11n-pose.pt')!=summary['weight_sha256'] or sha(root/'scripts/probe_site03_pose.py')!=summary['script_sha256']:raise ValueError('pose model or code changed; rerun probe')
expected={k[:-4] for k in FILES if k.endswith('.mp4')}
if {x['camera'] for x in summary['cameras']}!=expected or len(summary['cameras'])!=len(expected):raise ValueError('camera coverage mismatch')
for entry in summary['cameras']:
 cam=entry['camera'];video=raw/(cam+'.mp4');track=tracking/(cam+'_observations.csv');path=pose/(cam+'_track_pose.csv')
 if not valid(video,FILES[video.name]) or sha(track)!=entry['track_sha256'] or sha(path)!=entry['pose_csv_sha256'] or entry['video_sha256']!=FILES[video.name][1]:raise ValueError('cached evidence mismatch '+cam)
 with track.open() as f:tracks=list(csv.DictReader(f))
 with path.open() as f:rows=list(csv.DictReader(f))
 keys={(int(r['frame']),int(r['local_id'])) for r in rows};track_keys={(int(r['frame']),int(r['local_id'])) for r in tracks}
 if len(keys)!=len(rows) or len(track_keys)!=len(tracks) or keys!=track_keys or len(rows)!=entry['observations'] or dict(Counter(r['status'] for r in rows))!=entry['status_counts']:raise ValueError('pose coverage mismatch '+cam)
 unique=[(int(r['frame']),int(r['pose_index'])) for r in rows if r['status']=='unique']
 if len(set(unique))!=len(unique) or any(r['status'] not in ('unique','ambiguous','no_candidate') for r in rows):raise ValueError('pose correspondence mismatch '+cam)
print('site03 pose evidence PASS',sum(c['observations'] for c in summary['cameras']),'observations')
