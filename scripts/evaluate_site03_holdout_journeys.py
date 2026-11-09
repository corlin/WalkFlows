"""Build research journeys on 007 using its own observations, not reference IDs."""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,itertools,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));sys.path.insert(0,str(root/'scripts'))
from walkflows.artifact_cache import sha256
from walkflows.crossview import unique_pairs,summarize_pairs
from walkflows.journeys import build_hypotheses
from walkflows.reference_eval import convert_reference
from walkflows.scene_reference_coverage import compare_scene
from walkflows.site03_holdout_mode import resolve_mode
from fetch_site03_holdout import FILES,OUT
from fetch_site03_sample import valid
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--all-cameras',action='store_true',help='evaluate the separate six-camera comparison');args=parser.parse_args();cameras,folder_name=resolve_mode(args.all_cameras)
p=root/'data/processed'/folder_name;report=json.loads((p/'report.json').read_text());reference=OUT/'ground-truth.json'
if not valid(reference,FILES[reference.name]) or report['reference_sha256']!=sha256(reference) or report['script_sha256']!=sha256(root/'scripts/compare_site03_holdout.py') or report.get('mode_sha256')!=sha256(root/'walkflows/site03_holdout_mode.py') or report.get('all_cameras')!=args.all_cameras or len(report['cameras'])!=len(cameras) or {x['camera'] for x in report['cameras']}!=set(cameras):raise ValueError('stale inference evidence')
refs=convert_reference(json.loads(reference.read_text())['track_results'])['by_frame'];result={'scope':('six-camera same-site research hypotheses; not verified identities or people' if args.all_cameras else 'two-camera same-site research hypotheses; not verified identities or people'),'script_sha256':sha256(Path(__file__)),'mode_sha256':sha256(root/'walkflows/site03_holdout_mode.py'),'all_cameras':args.all_cameras,'reference_sha256':sha256(reference),'inference_report_sha256':sha256(p/'report.json'),'methods':{}}
for method in ('baseline','direct'):
 observations=[];frames={}
 for cam in report['cameras']:
  camera=cam['camera'];path=p/(camera+'_'+method+'_floor.json')
  if sha256(path)!=cam['methods'][method]['floor_sha256'] or not valid(OUT/(camera+'.mp4'),FILES[camera+'.mp4']):raise ValueError('stale observations')
  rows=json.loads(path.read_text());observations.extend(rows);group=defaultdict(list)
  for row in rows:group[row['frame']].append({'id':row['id'],'x':row['x'],'y':row['y']})
  frames[camera]=group
 edges=[];evidence=[]
 for left,right in itertools.combinations(sorted(frames),2):
  pairs=[]
  for f in sorted(frames[left].keys()&frames[right].keys()):pairs.extend({'frame':f,**x} for x in unique_pairs(frames[left][f],frames[right][f],max_distance=.5))
  pair_evidence=summarize_pairs(pairs,min_frames=10,min_consecutive=5)
  edges.extend({'left_camera':left,'right_camera':right,'left_id':e['left_id'],'right_id':e['right_id'],'supported':e['supported']} for e in pair_evidence)
  evidence.extend(({'left_camera':left,'right_camera':right,**e} if args.all_cameras else e) for e in pair_evidence)
 built=build_hypotheses(observations,edges,max_spread=.5);used=[(s['camera'],s['id'],sample['frame']) for h in built['hypotheses'] for sample in h['samples'] for s in sample['sources']];expected={(x['camera'],x['id'],x['frame']) for x in observations}
 if len(used)!=len(expected) or set(used)!=expected:raise ValueError('observation conservation failure')
 coverage=compare_scene(built['hypotheses'],refs,500,.5);path=p/(method+'-hypotheses.json');path.write_text(json.dumps(built,indent=2,allow_nan=False));(p/(method+'-coverage.json')).write_text(json.dumps(coverage,indent=2))
 result['methods'][method]={'hypotheses_sha256':sha256(path),'source_observations':len(observations),'hypotheses':len(built['hypotheses']),'multicamera_hypotheses':sum(len(h['members'])>1 for h in built['hypotheses']),'samples':dict(Counter(s['status'] for h in built['hypotheses'] for s in h['samples'])),'pairs':evidence,'coverage':{k:v for k,v in coverage.items() if k!='frames'}}
ref_tracks=defaultdict(list)
for frame,items in refs.items():
 for item in items:ref_tracks[item['id']].append({'frame':frame,'status':'research_candidate','x':item['x'],'y':item['y'],'sources':[{'kind':'published_reference','id':item['id']}]})
ref_path=p/'reference-hypotheses.json';ref_path.write_text(json.dumps({'hypotheses':[{'id':'reference-'+str(i),'members':[],'samples':samples} for i,samples in sorted(ref_tracks.items())]},indent=2));result['reference_hypotheses_sha256']=sha256(ref_path);(p/'journey-report.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
