"""Evaluate short-overlap local tracklet links without changing the default pipeline."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.tracklet_links import propose_links
from walkflows.stitched_journeys import stitch
from scripts.fetch_site03_sample import FILES
p=root/'data/processed';tracks=p/'site03-gpu-conf010';hpath=p/'site03-hypotheses/hypotheses.json';hmeta=p/'site03-hypotheses/summary.json';hybrid=p/'site03-hybrid-continuity/hypotheses.json';hybridmeta=p/'site03-hybrid-continuity/summary.json';out=p/'site03-tracklet-experiment';out.mkdir(parents=True,exist_ok=True);sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
if sha(hpath)!=json.loads(hmeta.read_text())['artifact_sha256'] or sha(hybrid)!=json.loads(hybridmeta.read_text())['artifact_sha256']:raise ValueError('hypothesis hash mismatch')
rows=[];input_hashes={}
for video_name in sorted(name for name in FILES if name.endswith('.mp4')):
 camera=video_name[:-4];path=tracks/(camera+'_observations.csv');meta=json.loads((tracks/(camera+'_run.json')).read_text())
 if sha(path)!=meta['observations_sha256']:raise ValueError('tracking hash mismatch')
 input_hashes[camera]=sha(path)
 with path.open() as f:
  for r in csv.DictReader(f):rows.append({'camera':camera,'local_id':int(r['local_id']),'frame':int(r['frame']),**{k:float(r[k]) for k in ('left','top','right','bottom')}})
links=propose_links(rows,min_shared=3,max_shared=10,iou_threshold=.6)
results={}
for name,source in [('pose',hpath),('hybrid_strict',hybrid)]:
 original=json.loads(source.read_text())['hypotheses'];linked=stitch(original,links,.5);dest=out/(name+'-linked.json');dest.write_text(json.dumps({'scope':'Experimental local-link hypotheses; unvalidated identities and counts.','hypotheses':linked},indent=2,allow_nan=False))
 before={(p['camera'],p['id'],s['frame']) for h in original for s in h['samples'] for p in s['sources']};after=[(p['camera'],p['id'],s['frame']) for h in linked for s in h['samples'] for p in s['sources']]
 if len(before)!=len(after) or before!=set(after):raise ValueError('source conservation failure')
 results[name]={'original_hypotheses':len(original),'linked_hypotheses':len(linked),'samples':sum(len(h['samples']) for h in linked),'states':dict(Counter(s['status'] for h in linked for s in h['samples'])),'reasons':dict(Counter(s['reason'] for h in linked for s in h['samples'] if s['reason'])),'artifact_sha256':sha(dest)}
report={'scope':'Same-camera overlap handoff candidates; not validated identity or customer counts.','settings':{'min_shared_frames':3,'max_shared_frames':10,'iou_threshold':.6},'links':links,'results':results,'inputs':{'pose_sha256':sha(hpath),'hybrid_sha256':sha(hybrid),'track_sha256':input_hashes}}
(out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
