"""Rebuild and verify the fixed site03 research chain, without downloads or training."""
from pathlib import Path
import argparse,csv,hashlib,json,math,subprocess,sys,time
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'scripts'))
from fetch_site03_sample import FILES,valid
from fetch_site03_calibration import files as calibration,valid as valid_calibration
from fetch_site03_native_header import valid as valid_native_header
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--site03-only',action='store_true',help='skip optional site02 cross-scene comparisons');args=parser.parse_args()
out=root/'data/processed/site03-verification';out.mkdir(parents=True,exist_ok=True)
report={'status':'running','scope':'Reproducible research outputs only; no claim of physical accuracy, identity validation or customer counts.','site03_only':args.site03_only,'skipped':[],'steps':[]}
def save():
 temp=out/'report.json.tmp';temp.write_text(json.dumps(report,indent=2));temp.replace(out/'report.json')
def step(name,command):
 start=time.perf_counter();p=subprocess.run(command,cwd=root,capture_output=True,text=True)
 (out/(name+'.log')).write_text(p.stdout+p.stderr);report['steps'].append({'name':name,'exit_code':p.returncode,'elapsed_s':time.perf_counter()-start});save();print(name,'PASS' if p.returncode==0 else 'FAIL',flush=True)
 if p.returncode:report['status']='failed';save();raise SystemExit(p.returncode)
try:
 raw=root/'data/raw/multiview/006_site03_tracks';assets=root/'data/upstream-research'
 if not all(valid(raw/name,meta) for name,meta in FILES.items()):raise ValueError('missing or corrupt sample; run fetch_site03_sample.py')
 if not all(valid_calibration(assets/Path(name).name,digest) for name,digest in calibration.items()):raise ValueError('missing or corrupt calibration; run fetch_site03_calibration.py')
 if not valid_native_header(assets/'calibration-utils.hpp'):raise ValueError('missing or corrupt native header; run fetch_site03_native_header.py')
 for name in ('probe_native_lift.py','audit_site03_reference.py','probe_site03.py','probe_site03_floor.py','evaluate_site03_reference.py','probe_site03_crossview.py','verify_site03_pose_evidence.py','compare_site03_pose_reference.py','compare_site03_pose_crossview.py','export_site03_pose_floor.py','probe_site03_pose_crossview.py','probe_site03_hybrid_foot.py','probe_site03_hybrid_crossview.py','verify_site02_pose_evidence.py','compare_site02_pose_cross_scene.py','probe_site02_hybrid_foot.py','evaluate_site02_hybrid.py','build_site03_hypotheses.py','evaluate_site03_hybrid_continuity.py','evaluate_site03_tracklets.py','diagnose_site03_associations.py','build_site03_review.py'):
  if args.site03_only and name in {'verify_site02_pose_evidence.py','compare_site02_pose_cross_scene.py','probe_site02_hybrid_foot.py','evaluate_site02_hybrid.py'}:
   report['skipped'].append(name);continue
  step(name,[sys.executable,str(root/'scripts'/name)])
 step('python-tests',[sys.executable,'-m','unittest','discover','-s','tests'])
 for name in ('test_local_zones.js','test_reference_hysteresis.js','test_reference_route.js','test_layout.js','test_layout_canvas.js','test_example_flow_layout.js','test_track_events.js','test_track_report.js','test_track_events_integration.js','test_site03_events.js','test_hypothesis_analytics.js','test_analysis_window.js','test_reference_tracks.js','test_zone_transitions.js','test_interrupted_transitions.js','test_source_comparison.js','test_quality_report.js','test_site03_hypothesis_integration.js','test_research_funnel.js'):
  if args.site03_only and name=='test_track_events_integration.js':report['skipped'].append(name);continue
  step(name,['node',str(root/'tests'/name)])
 d=json.loads((root/'data/processed/site03-review/data.json').read_text());e=json.loads((root/'data/processed/site03-reference-eval/summary.json').read_text());c=json.loads((root/'data/processed/site03-crossview/summary.json').read_text())
 assert json.loads((root/'data/processed/site03-reference-audit/summary.json').read_text())['coordinate_key_mismatches']==0
 assert len(d['cameras'])==6 and d['video_frames']==400 and d['reference_frames']==399 and len(e['empty_reference_track_ids'])==9
 assert {p['kind'] for p in d['pairs']}=={'box','pose','hybrid'}
 assert all('pose_candidate' in p and 'hybrid_candidate' in p for camera in d['cameras'].values() for p in camera)
 lookup={(cam,row['frame'],row['id']):row for cam,rows in d['cameras'].items() for row in rows}
 assert len(lookup)==sum(map(len,d['cameras'].values()))
 for pair in d['pairs']:
  a=lookup[(pair['left_camera'],pair['frame'],pair['left_id'])];b=lookup[(pair['right_camera'],pair['frame'],pair['right_id'])]
  if pair['kind']=='hybrid':
   assert a['hybrid_candidate'] and b['hybrid_candidate'];dx=a['hybrid_x']-b['hybrid_x'];dy=a['hybrid_y']-b['hybrid_y']
  elif pair['kind']=='pose':
   assert a['pose_candidate'] and b['pose_candidate'];dx=a['pose_x']-b['pose_x'];dy=a['pose_y']-b['pose_y']
  else:
   assert a['research_geometry_candidate'] and b['research_geometry_candidate'];dx=a['x']-b['x'];dy=a['y']-b['y']
  assert abs(math.hypot(dx,dy)-pair['distance'])<1e-9 and pair['distance']<=pair['threshold']
 assert e['candidate_matches_sha256']==hashlib.sha256((root/'data/processed/site03-reference-eval/candidate_matches.csv').read_bytes()).hexdigest()
 assert c['candidate_csv_sha256']==hashlib.sha256((root/'data/processed/site03-crossview/pair_candidates.csv').read_bytes()).hexdigest()
 report['evidence']={'cameras':len(d['cameras']),'video_frames_per_camera':d['video_frames'],'reference_frames':d['reference_frames'],'empty_reference_track_objects':len(e['empty_reference_track_ids']),'local_observations':sum(map(len,d['cameras'].values())),'crossview_pair_rows':len(d['pairs']),'research_hypotheses':len(d['hypotheses']),'review_json_sha256':hashlib.sha256((root/'data/processed/site03-review/data.json').read_bytes()).hexdigest()}
 report['status']='pass';save();print('site03 research verification PASS',flush=True)
except Exception as exc:
 report['status']='failed';report['error']=str(exc);save();raise
