"""Conditional site03 comparison to supplied floor tracks; not precision/recall."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,hashlib,json,math,statistics,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from walkflows.reference_eval import convert_reference,match_positions
from walkflows.crossview import local_duplicate_keys
from fetch_site03_sample import FILES,valid
raw=root/'data/raw/multiview/006_site03_tracks';source=raw/'ground-truth.json'
if not valid(source,FILES['ground-truth.json']):raise ValueError('reference checksum mismatch')
reference=json.loads(source.read_text())['track_results'];parsed=convert_reference(reference);by_frame=parsed['by_frame']
if reference.get('start-frame')!=0:raise ValueError('unexpected reference start')
if abs(parsed['frame_duration']-1/15)>1e-8:raise ValueError('unexpected reference rate')
projection=root/'data/processed/site03-floor-probe';summary=json.loads((projection/'summary.json').read_text());out=root/'data/processed/site03-reference-eval';out.mkdir(parents=True,exist_ok=True)
rows=[];reports=[]
for entry in summary['cameras']:
 if entry['status']!='complete':reports.append({'camera':entry['camera'],'status':'missing projection'});continue
 camera=entry['camera'];path=projection/(camera+'_experimental_floor.csv')
 if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['projection_sha256']:raise ValueError('projection checksum mismatch')
 with path.open() as f: observations=list(csv.DictReader(f))
 raw_path=root/'data/processed/site03-gpu-conf010'/(camera+'_observations.csv')
 if hashlib.sha256(raw_path.read_bytes()).hexdigest()!=entry['source_sha256']:raise ValueError('tracking checksum mismatch')
 with raw_path.open() as f: boxes=list(csv.DictReader(f))
 duplicate_keys=local_duplicate_keys([{'frame':int(r['frame']),'id':int(r['local_id']),'box':tuple(float(r[k]) for k in ('left','top','right','bottom'))} for r in boxes],containment=0.9)
 grouped=defaultdict(list);outside=invalid=duplicates=0
 for r in observations:
  frame=int(r['frame']);x=float(r['experimental_x']);y=float(r['experimental_y'])
  if frame not in by_frame:outside+=1;continue
  if (frame,int(r['local_id'])) in duplicate_keys:duplicates+=1;continue
  if not all(int(r[k])==1 for k in ('inside_calibration_hull','forward_nonparallel','in_scene_bounds')) or not math.isfinite(x) or not math.isfinite(y):invalid+=1;continue
  grouped[frame].append({'id':int(r['local_id']),'x':x,'y':y})
 eligible=sum(map(len,grouped.values()));cam_result={'camera':camera,'status':'complete','all_observations':len(observations),'outside_reference_frames':outside,'geometry_excluded':invalid,'duplicate_excluded':duplicates,'eligible_observations':eligible,'thresholds':[]}
 for threshold in (0.25,0.5,1.0):
  matches=[];ambiguous=0;by_local=defaultdict(Counter)
  for frame,predictions in sorted(grouped.items()):
   refs=by_frame[frame];mapping=match_positions(predictions,refs,threshold)
   for m in mapping:
    pred=next(x for x in predictions if x['id']==m['prediction_id']);near=sum(math.hypot(pred['x']-ref['x'],pred['y']-ref['y'])<=threshold for ref in refs);ambiguous+=near>1
    record={'camera':camera,'frame':frame,'threshold':threshold,'local_id':m['prediction_id'],'reference_id':m['reference_id'],'distance':m['distance'],'multiple_reference_candidates':near>1}
    matches.append(record);rows.append(record);by_local[m['prediction_id']][m['reference_id']]+=1
  distances=sorted(x['distance'] for x in matches)
  local=[{'local_id':ident,'matched_frames':sum(counts.values()),'reference_distribution':dict(sorted(counts.items())),'modal_share':max(counts.values())/sum(counts.values())} for ident,counts in sorted(by_local.items())]
  cam_result['thresholds'].append({'distance_threshold':threshold,'proximity_matched_observations':len(matches),'eligible_observations':eligible,'multiple_reference_candidates':ambiguous,'distance_median':statistics.median(distances) if distances else None,'distance_p90':float(__import__('numpy').percentile(distances,90)) if distances else None,'per_local_track':local})
 reports.append(cam_result)
fields=['camera','frame','threshold','local_id','reference_id','distance','multiple_reference_candidates']
with (out/'candidate_matches.csv').open('w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
point_counts=[len(v) for v in by_frame.values()]
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'scene_sha256':summary['scene_sha256'],'reference_frames':reference['frames'],'video_frames_expected':400,'outside_reference_frame_policy':'unknown, not negative','reference_track_objects':parsed['track_count'],'empty_reference_track_ids':parsed['empty_track_ids'],'reference_points':sum(point_counts),'reference_frames_with_multiple_points':sum(v>1 for v in point_counts),'max_reference_points_in_frame':max(point_counts),'thresholds_are':'exploratory scene coordinate distance gates; not validated accuracy criteria','assumptions':['same clip frame index as reference; no offset optimization','same scene coordinate convention; physical alignment unverified','camera visibility and annotation completeness unknown','one-to-one matching is camera-local and provisional; not validated identity'], 'not_metrics':['unmatched reference is not a camera miss','matched fraction is not precision, recall, or identity accuracy'], 'cameras':reports,'candidate_matches_sha256':hashlib.sha256((out/'candidate_matches.csv').read_bytes()).hexdigest()}
(out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
