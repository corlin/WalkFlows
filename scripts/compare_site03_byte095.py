"""Compare existing ByteTrack and ByteTrack 0.95 outputs by mutually unique box overlap."""
from pathlib import Path
import csv,hashlib,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.tracker_comparison import compare
base=root/'data/processed/site03-gpu-conf010';other=root/'data/processed/site03-byte095-experiment';reports=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
 with path.open(newline='') as f:return [{k:int(v) if k in ('frame','local_id') else float(v) for k,v in row.items()} for row in csv.DictReader(f)]
for camera in ('C0001055_v4','C0001056_v2'):
 left=base/(camera+'_observations.csv');right=other/(camera+'_observations.csv');lrun=json.loads((base/(camera+'_run.json')).read_text());rrun=json.loads((other/(camera+'_run.json')).read_text())
 if sha(left)!=lrun['observations_sha256'] or sha(right)!=rrun['observations_sha256']:raise ValueError('observation hash mismatch')
 for key in ('video_sha256','weights_sha256','conf','imgsz','torch','ultralytics','opencv'):
  if lrun['contract'][key]!=rrun['contract'][key]:raise ValueError('incomparable '+key)
 if lrun['contract']['tracker']!='bytetrack.yaml' or not rrun['contract']['tracker'].endswith('byte095.yaml'):raise ValueError('unexpected tracker')
 a,b=load(left),load(right)
 reports.append({'camera':camera,'byte_observations':len(a),'relaxed_observations':len(b),'byte_ids':len({r['local_id'] for r in a}),'relaxed_ids':len({r['local_id'] for r in b}),'byte_sha256':sha(left),'relaxed_sha256':sha(right),'byte_config_sha256':lrun['contract']['tracker_config_sha256'],'relaxed_config_sha256':rrun['contract']['tracker_config_sha256'],'comparison':compare(a,b,.8)})
report={'scope':'Same-frame mutually unique box correspondence only, not identity accuracy or independent validation.','threshold_iou':.8,'cameras':reports};(other/'comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
