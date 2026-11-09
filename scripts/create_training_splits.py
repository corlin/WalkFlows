"""Create a reproducible site-isolated inventory before training."""
from pathlib import Path
import hashlib,json,os,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.dataset_splits import build_splits,SITE_SPLITS
from walkflows.artifact_cache import sha256
source=root/'data/processed/multiview-inventory/manifest.json';output=source.parent/'site-splits.json'
data=json.loads(source.read_text())
if data['revision']!='6cf0e1066653f7efe1d0aae5c49860b19ef9a6e5' or data['files']!=len(data['entries']):raise ValueError('invalid pinned manifest')
splits=build_splits(data['entries'])
result={'scope':'site-isolated file inventory, not yet a validated training dataset','revision':data['revision'],'manifest_sha256':sha256(source),'site_splits':SITE_SPLITS,'shared_policy':'calibration and repository files are shared resources, not training labels','summary':{name:{'files':len(entries),'bytes':sum(e['size'] for e in entries),'videos':sum(e['path'].endswith('.mp4') for e in entries),'floor_reference_files':sum(e['path'].endswith('/ground-truth.json') for e in entries)} for name,entries in splits.items()},'splits':splits}
tmp=output.with_suffix('.json.tmp');tmp.write_text(json.dumps(result,indent=2));os.replace(tmp,output);print(json.dumps(result['summary'],indent=2))
