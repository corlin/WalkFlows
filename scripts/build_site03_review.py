"""Build local site03 two-camera research review with provenance-checked inputs."""
from pathlib import Path
import csv,hashlib,json,os,shutil,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from fetch_site03_sample import FILES,valid
from walkflows.reference_eval import convert_reference
from walkflows.association_review import review_events
from walkflows.crossview import local_duplicate_keys
raw=root/'data/raw/multiview/006_site03_tracks';floor=root/'data/processed/site03-floor-probe';tracks=root/'data/processed/site03-gpu-conf010';cross=root/'data/processed/site03-crossview';out=root/'data/processed/site03-review';out.mkdir(parents=True,exist_ok=True)
pose=root/'data/processed/site03-pose-floor';posecross=root/'data/processed/site03-pose-proposals';hypdir=root/'data/processed/site03-hypotheses';hybrid=root/'data/processed/site03-hybrid-foot';hybridcross=root/'data/processed/site03-hybrid-proposals'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary=json.loads((floor/'summary.json').read_text());cross_summary=json.loads((cross/'summary.json').read_text());pairfile=cross/'pair_candidates.csv';reference=raw/'ground-truth.json';scene=root/'data/upstream-research/site03_scene03.json'
if not valid(reference,FILES['ground-truth.json']) or sha(pairfile)!=cross_summary['candidate_csv_sha256'] or sha(floor/'summary.json')!=cross_summary['inputs']['floor_summary_sha256'] or sha(scene)!=summary['scene_sha256']:raise ValueError('input provenance mismatch')
reference_summary_path=root/'data/processed/site03-reference-eval/summary.json';reference_summary=json.loads(reference_summary_path.read_text())
pose_summary=json.loads((pose/'summary.json').read_text());pose_cross_summary=json.loads((posecross/'summary.json').read_text());pose_pairfile=posecross/'pair_candidates.csv'
if sha(pose_pairfile)!=pose_cross_summary['candidate_csv_sha256'] or sha(pose/'summary.json')!=pose_cross_summary['pose_floor_summary_sha256'] or sha(reference_summary_path)!=pose_cross_summary['reference_summary_sha256'] or sha(reference_summary_path)!=cross_summary['inputs']['reference_summary_sha256'] or sha(reference)!=reference_summary['source_sha256'] or pose_summary['scene_sha256']!=summary['scene_sha256']:raise ValueError('pose candidate provenance mismatch')
hyp_summary=json.loads((hypdir/'summary.json').read_text());hyp_path=hypdir/'hypotheses.json'
if sha(hyp_path)!=hyp_summary['artifact_sha256']:raise ValueError('hypotheses provenance mismatch')
hypotheses=json.loads(hyp_path.read_text())
if hypotheses['inputs']['pose_floor_summary_sha256']!=sha(pose/'summary.json') or hypotheses['inputs']['proposal_summary_sha256']!=sha(posecross/'summary.json'):raise ValueError('stale hypotheses inputs')
diagnostic_path=root/'data/processed/site03-association-diagnostic/summary.json';diagnostic=json.loads(diagnostic_path.read_text())
if diagnostic['inputs']['reference_sha256']!=sha(reference) or diagnostic['inputs']['hypotheses_sha256']!=sha(hyp_path):raise ValueError('stale association diagnostic')
association_review=review_events(diagnostic,hypotheses['hypotheses'])
linked_path=root/'data/processed/site03-tracklet-experiment/pose-linked.json';linked_summary=json.loads((linked_path.parent/'summary.json').read_text())
if linked_summary['inputs']['pose_sha256']!=sha(hyp_path) or linked_summary['results']['pose']['artifact_sha256']!=sha(linked_path):raise ValueError('stale local-link experiment')
linked_hypotheses=json.loads(linked_path.read_text())['hypotheses']
hybrid_summary=json.loads((hybrid/'summary.json').read_text());hybrid_cross_summary=json.loads((hybridcross/'summary.json').read_text());hybrid_data=hybrid/'observations.jsonl';hybrid_pairfile=hybridcross/'pair_candidates.csv'
if sha(hybrid_data)!=hybrid_summary['observations_sha256'] or sha(hybrid/'summary.json')!=hybrid_cross_summary['hybrid_summary_sha256'] or sha(hybrid_pairfile)!=hybrid_cross_summary['candidate_csv_sha256'] or sha(reference_summary_path)!=hybrid_cross_summary['reference_summary_sha256'] or sha(pose/'summary.json')!=hybrid_summary['pose_summary_sha256'] or sha(floor/'summary.json')!=hybrid_summary['floor_summary_sha256']:raise ValueError('hybrid provenance mismatch')
hybrid_rows=[json.loads(line) for line in hybrid_data.read_text().splitlines()];hybrid_map={(r['camera'],r['frame'],r['local_id']):r for r in hybrid_rows}
if len(hybrid_map)!=len(hybrid_rows):raise ValueError('duplicate hybrid observations')
pose_entries={c['camera']:c for c in pose_summary['cameras']}
if any(c['status']!='complete' for c in summary['cameras']):raise ValueError('incomplete camera processing')
reference_frames=convert_reference(json.loads(reference.read_text())['track_results'])['by_frame'];camera_data={}
for entry in summary['cameras']:
 camera=entry['camera'];video=raw/(camera+'.mp4');boxpath=tracks/(camera+'_observations.csv');projectpath=floor/(camera+'_experimental_floor.csv')
 if not valid(video,FILES[video.name]) or sha(boxpath)!=entry['source_sha256'] or sha(projectpath)!=entry['projection_sha256']:raise ValueError('camera input mismatch '+camera)
 with boxpath.open() as f:boxes=list(csv.DictReader(f))
 with projectpath.open() as f:points=list(csv.DictReader(f))
 posepath=pose/(camera+'_pose_floor.csv');pose_entry=pose_entries[camera]
 if sha(posepath)!=pose_entry['output_sha256'] or pose_entry['track_csv_sha256']!=entry['source_sha256']:raise ValueError('pose input mismatch '+camera)
 with posepath.open() as f:pose_rows=list(csv.DictReader(f))
 posemap={(int(x['frame']),int(x['local_id'])):x for x in pose_rows}
 boxmap={(int(x['frame']),int(x['local_id'])):x for x in boxes};pointmap={(int(x['frame']),int(x['local_id'])):x for x in points}
 if len(boxmap)!=len(boxes) or len(pointmap)!=len(points) or len(posemap)!=len(pose_rows) or set(boxmap)!=set(pointmap) or set(boxmap)!=set(posemap):raise ValueError('track/projection keys mismatch')
 dups=local_duplicate_keys([{'frame':k[0],'id':k[1],'box':tuple(float(v[n]) for n in ('left','top','right','bottom'))} for k,v in boxmap.items()],containment=.9)
 output=[]
 for key,box in boxmap.items():
  p=pointmap[key];pose_row=posemap[key];hybrid_row=hybrid_map[(camera,*key)];good=key not in dups and all(int(p[k])==1 for k in ('inside_calibration_hull','forward_nonparallel','in_scene_bounds'))
  output.append({'frame':key[0],'id':key[1],'box':[float(box[k]) for k in ('left','top','right','bottom')],'x':float(p['experimental_x']),'y':float(p['experimental_y']),'research_geometry_candidate':good,'pose_x':float(pose_row['floor_x']) if pose_row['floor_x'] else None,'pose_y':float(pose_row['floor_y']) if pose_row['floor_y'] else None,'pose_pixel_x':float(pose_row['foot_x']) if pose_row['foot_x'] else None,'pose_pixel_y':float(pose_row['foot_y']) if pose_row['foot_y'] else None,'pose_candidate':bool(int(pose_row['research_candidate'])),'pose_status':pose_row['pose_status'],'pose_reason':pose_row['exclusion_reasons'],'hybrid_x':hybrid_row['x'],'hybrid_y':hybrid_row['y'],'hybrid_candidate':hybrid_row['x'] is not None,'hybrid_method':hybrid_row['method'],'hybrid_reasons':hybrid_row['reasons']})
 camera_data[camera]=output
 dest=out/video.name
 if not valid(dest,FILES[video.name]):
  tmp=out/(video.name+'.tmp');shutil.copyfile(video,tmp)
  if not valid(tmp,FILES[video.name]):raise ValueError('copy checksum mismatch')
  os.replace(tmp,dest)
if len(hybrid_map)!=sum(len(rows) for rows in camera_data.values()):raise ValueError('hybrid coverage mismatch')
pairs=[]
for kind,path in [('box',pairfile),('pose',pose_pairfile),('hybrid',hybrid_pairfile)]:
 with path.open() as f:pairs.extend({'kind':kind,'threshold':float(r['threshold']),'frame':int(r['frame']),'left_camera':r['left_camera'],'left_id':int(r['left_id']),'right_camera':r['right_camera'],'right_id':int(r['right_id']),'distance':float(r['distance']),'proxy':r['reference_proximity_proxy'],'left_method':r.get('left_method',''),'right_method':r.get('right_method','')} for r in csv.DictReader(f))
obj={'scene':'site03_scene03','bounds':json.loads(scene.read_text())['hist-aabb'],'cameras':camera_data,'hypotheses':hypotheses['hypotheses'],'linked_hypotheses':linked_hypotheses,'research_metadata':{'reference_sha256':sha(reference),'linked_hypothesis_sha256':sha(linked_path),'hypothesis_sha256':hyp_summary['artifact_sha256'],'inputs':hypotheses['inputs'],'scene_sha256':summary['scene_sha256'],'association_threshold':hypotheses['association_threshold'],'max_frame_spread':hypotheses['max_frame_spread'],'pose_score_threshold':pose_summary['pose_score_threshold']},'association_review':association_review,'association_review_sha256':sha(diagnostic_path),'associations':hypotheses['associations'],'pairs':pairs,'reference':reference_frames,'reference_frames':len(reference_frames),'video_frames':400,'fps':15,'scope':'experimental camera-local projections and pair candidates; no accepted identities or customer counts'}
tmp=out/'data.json.tmp';tmp.write_text(json.dumps(obj,allow_nan=False));os.replace(tmp,out/'data.json')
shutil.copyfile(root/'walkflows/site03_review.html',out/'index.html')
for name in ('layout.js','local_zones.js','site03_events.js','hypothesis_analytics.js','research_funnel.js','zone_transitions.js','source_comparison.js'):shutil.copyfile(root/'walkflows'/name,out/name)
print('built',out,'cameras',len(camera_data),'observations',sum(map(len,camera_data.values())),'pair rows',len(pairs))
