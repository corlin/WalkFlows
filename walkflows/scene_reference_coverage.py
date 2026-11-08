"""Framewise global spatial coverage against a partial published reference."""
from collections import defaultdict
from walkflows.reference_eval import match_positions, finite

def compare_scene(hypotheses, reference, frame_count, threshold):
    if type(frame_count) is not int or frame_count < 1 or not finite(threshold) or threshold <= 0:
        raise ValueError("invalid coverage settings")
    if not isinstance(reference, dict) or any(type(f) is not int or f < 0 or f >= frame_count for f in reference):
        raise ValueError("invalid reference frames")
    frames = defaultdict(list); conflicts = defaultdict(list); ids = set()
    for hypothesis in hypotheses:
        ident = hypothesis['id']
        if not isinstance(ident, str) or not ident or ident in ids: raise ValueError("invalid hypothesis ID")
        ids.add(ident); seen = set()
        for sample in hypothesis['samples']:
            frame = sample['frame']
            if type(frame) is not int or not 0 <= frame < frame_count or frame in seen: raise ValueError("invalid sample frame")
            seen.add(frame); status = sample['status']
            if status == 'spatial_conflict':
                if sample['x'] is not None or sample['y'] is not None: raise ValueError("conflict has position")
                conflicts[frame].append(ident)
            elif status == 'research_candidate' and finite(sample['x']) and finite(sample['y']):
                frames[frame].append({'id':ident,'x':sample['x'],'y':sample['y']})
            else: raise ValueError("invalid sample")
    result = {'matched':0,'unmatched_predictions':0,'unmatched_reference':0,'conflicts':0,'outside_reference':0,'frames':[]}
    for frame in range(frame_count):
        predictions=frames[frame]; blocked=conflicts[frame]
        result['conflicts'] += len(blocked)
        if frame not in reference:
            result['outside_reference'] += len(predictions)
            result['frames'].append({'frame':frame,'status':'reference_unavailable','prediction_ids':[p['id'] for p in predictions],'conflict_ids':blocked})
            continue
        refs=reference[frame]; matches=match_positions(predictions,refs,threshold)
        pred_ids={m['prediction_id'] for m in matches}; ref_ids={m['reference_id'] for m in matches}
        unmatched_p=[p['id'] for p in predictions if p['id'] not in pred_ids]
        unmatched_r=[p['id'] for p in refs if p['id'] not in ref_ids]
        result['matched'] += len(matches); result['unmatched_predictions'] += len(unmatched_p); result['unmatched_reference'] += len(unmatched_r)
        result['frames'].append({'frame':frame,'status':'compared','matches':matches,'unmatched_prediction_ids':unmatched_p,'unmatched_reference_ids':unmatched_r,'conflict_ids':blocked})
    return result
