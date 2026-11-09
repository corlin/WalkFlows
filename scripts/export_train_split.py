"""Export available labeled training scenarios, recording partial failures."""
from pathlib import Path
import json,os,subprocess,sys,time
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.artifact_cache import sha256
state=root/'data/processed/multiview-inventory';manifest=state/'manifest.json';splits_path=state/'site-splits.json';splits=json.loads(splits_path.read_text())
if splits['manifest_sha256']!=sha256(manifest):raise ValueError('stale split')
scenarios=sorted({e['path'].split('/')[1] for e in splits['splits']['train'] if e['path'].startswith('testcases/') and e['path'].endswith('/ground-truth.json')})
if not scenarios:raise ValueError('no labeled training scenarios')
out=root/'data/processed/weak-position-labels';out.mkdir(parents=True,exist_ok=True);report_path=out/'training-batch.json';report={'scope':'weak spatial proxies; not ground-truth per-camera identities','status':'running','splits_sha256':sha256(splits_path),'exporter_sha256':sha256(root/'scripts/export_weak_position_labels.py'),'scenarios':[]}
def save():
 tmp=report_path.with_suffix('.json.tmp');tmp.write_text(json.dumps(report,indent=2));os.replace(tmp,report_path)
save()
for i,scenario in enumerate(scenarios,1):
 start=time.perf_counter();result=subprocess.run([sys.executable,str(root/'scripts/export_weak_position_labels.py'),'--scenario',scenario],cwd=root,capture_output=True,text=True);folder=out/scenario;folder.mkdir(parents=True,exist_ok=True);(folder/'batch.log').write_text(result.stdout+result.stderr);report['scenarios'].append({'scenario':scenario,'exit_code':result.returncode,'elapsed_s':time.perf_counter()-start});save();print(i,'/',len(scenarios),scenario,'OK' if result.returncode==0 else 'FAILED',flush=True)
report['status']='complete' if all(x['exit_code']==0 for x in report['scenarios']) else 'incomplete';save();print('Batch',report['status'],flush=True)
if report['status']!='complete':raise SystemExit(1)
