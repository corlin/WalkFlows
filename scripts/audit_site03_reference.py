"""Audit published site03 track objects and annotation coordinate agreement."""
from pathlib import Path
import collections,hashlib,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from fetch_site03_sample import FILES,valid
from walkflows.reference_eval import convert_reference
raw=root/'data/raw/multiview/006_site03_tracks';ref=raw/'ground-truth.json';annotations=raw/'annotation-data.json'
for file in (ref,annotations):
 if not valid(file,FILES[file.name]):raise ValueError('input hash mismatch: '+file.name)
gt=json.loads(ref.read_text())['track_results'];info=convert_reference(gt);state=json.loads(annotations.read_text())['state'];annotations_by_key={}
for row in state['ltps']:
 point=row['tp'];key=(row['track_id'],point[2])
 if key in annotations_by_key:raise ValueError('duplicate annotation id/frame')
 annotations_by_key[key]=tuple(point[:2])
reference_by_key={}
for track in gt['tracks']:
 for point in track['path']:reference_by_key[(track['id'],point[2])]=tuple(point[:2])
keys=reference_by_key.keys()|annotations_by_key.keys();mismatch=sum(reference_by_key.get(k)!=annotations_by_key.get(k) for k in keys)
counts=collections.Counter(len(t['path']) for t in gt['tracks']);counts={str(k):v for k,v in sorted(counts.items())}
report={'scope':'Existing annotation/reference coordinate consistency only; not a video identity or physical accuracy validation.','ground_truth_sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'annotation_sha256':hashlib.sha256(annotations.read_bytes()).hexdigest(),'track_objects':len(gt['tracks']),'track_lengths':counts,'empty_ids':info['empty_track_ids'],'annotation_points':len(annotations_by_key),'reference_points':len(reference_by_key),'coordinate_key_mismatches':mismatch,'reference_frame_count':gt['frames'],'reference_start_frame':gt['start-frame'],'video_frame_count':400}
out=root/'data/processed/site03-reference-audit';out.mkdir(parents=True,exist_ok=True);(out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
