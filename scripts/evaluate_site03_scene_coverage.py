"""One-to-one scene-wide spatial comparison; not validated tracking metrics."""
from pathlib import Path
import hashlib, json, sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root));sys.path.insert(0,str(root/'scripts'))
from fetch_site03_sample import FILES,valid
from walkflows.reference_eval import convert_reference
from walkflows.scene_reference_coverage import compare_scene
raw=root/'data/raw/multiview/006_site03_tracks/ground-truth.json'
hyp=root/'data/processed/site03-hypotheses/hypotheses.json'
summary=root/'data/processed/site03-hypotheses/summary.json'
if not valid(raw,FILES['ground-truth.json']): raise ValueError('reference checksum mismatch')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if digest(hyp)!=json.loads(summary.read_text())['artifact_sha256']: raise ValueError('hypothesis checksum mismatch')
reference=json.loads(raw.read_text())['track_results']
if reference['start-frame']!=0 or reference['frames']!=399: raise ValueError('unexpected reference window')
parsed=convert_reference(reference); hypotheses=json.loads(hyp.read_text())['hypotheses']
report={'scope':'provisional scene-wide position matching; not precision, recall, identity or customer counts',
        'assumptions':['matching frame index and coordinate system','reference visibility and completeness unknown','distance gates are exploratory','spatial conflicts and frame 399 remain unknown'],
        'reference_sha256':digest(raw),'hypotheses_sha256':digest(hyp),'video_frames':400,'reference_frames':399,'thresholds':{}}
for threshold in (.25,.5,1.0):
    report['thresholds'][str(threshold)]=compare_scene(hypotheses,parsed['by_frame'],400,threshold)
out=root/'data/processed/site03-scene-reference-coverage';out.mkdir(parents=True,exist_ok=True)
(out/'report.json').write_text(json.dumps(report,indent=2))
for threshold,r in report['thresholds'].items(): print(threshold,{k:v for k,v in r.items() if k!='frames'})
