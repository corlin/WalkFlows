"""Audit selected training/validation scene transforms before model fitting."""
from pathlib import Path
import json,sys
import numpy as np
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.artifact_cache import sha256
from walkflows.scene_transforms import compose_camera,normalized_bounds
from scripts.fetch_multiview_dataset import digest
base=root/'data/raw/multiview/full-dataset';state=root/'data/processed/multiview-inventory';inventory=json.loads((state/'manifest.json').read_text());splits=json.loads((state/'site-splits.json').read_text())
if splits['manifest_sha256']!=sha256(state/'manifest.json') or splits['revision']!=inventory['revision']:raise ValueError('split provenance mismatch')
entries={x['path']:x for x in inventory['entries']}
def read(path):
 entry=entries[path];source=base/path
 if not digest(source,entry):raise ValueError('missing or corrupt dataset file '+path)
 return json.loads(source.read_text())
reports=[]
for split,scenario in (('train','045_site04_sitting_2'),('validation','011_site06_standing')):
 prefix='testcases/'+scenario+'/';allowed={x['path'] for x in splits['splits'][split]}
 if prefix+'manifest.json' not in allowed or prefix+'ground-truth.json' not in allowed:raise ValueError('scene outside fixed split')
 manifest=read(prefix+'manifest.json');reference=read(prefix+'ground-truth.json')['track_results'];scene_path='calibration/scenes/'+manifest['scene-key']+'.json';scene=read(scene_path);bounds=normalized_bounds(scene['hist-aabb']);origin=reference['top-left'];size=reference['hist-sz'];expected=[origin[0],origin[1],origin[0]+size*reference['width'],origin[1]+size*reference['height']]
 if not np.allclose(bounds,expected,atol=1e-4,rtol=0):raise ValueError('scene and reference bounds differ')
 cameras=[]
 for name,transform in zip(scene['bcam-keys'],scene['bcam-transforms'],strict=True):
  composed=compose_camera(transform,scene['global-transformation']);cameras.append({'camera':name,'raw_translation':transform['translation'],'composed_translation':composed['translation'],'composed_rotation':composed['rotation'],'scale':composed['scale']})
 if {x['camera'] for x in manifest['videos']}!=set(scene['bcam-keys']):raise ValueError('camera mismatch')
 reports.append({'split':split,'scenario':scenario,'scene':manifest['scene-key'],'raw_bounds':scene['hist-aabb'],'normalized_bounds':bounds,'reference_bounds':expected,'global_transformation':scene['global-transformation'],'cameras':cameras,'input_digests':{k:entries[k]['digest'] for k in (prefix+'manifest.json',prefix+'ground-truth.json',scene_path)}})
result={'scope':'source-aligned transform composition and reference bounds audit; not physical localization validation','inventory_sha256':sha256(state/'manifest.json'),'splits_sha256':sha256(state/'site-splits.json'),'scenes':reports};out=state/'scene-audit.json';out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
