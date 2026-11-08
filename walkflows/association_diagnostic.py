"""Conservative reference-proximity diagnostics; never identity ground truth."""
from collections import Counter
from math import hypot, isfinite

def diagnose(observations, references_by_frame, radius):
    if not isfinite(radius) or radius <= 0:
        raise ValueError('radius must be finite and positive')
    rows=[]; claims=Counter()
    for obs in observations:
        row=dict(obs, reference_id=None, status=None)
        refs=references_by_frame.get(obs['frame'])
        if refs is None:
            row['status']='reference_missing'
        else:
            nearby=[ref for ref in refs if hypot(obs['x']-ref['x'],obs['y']-ref['y'])<=radius]
            for ref in nearby: claims[(obs['camera'],obs['frame'],ref['id'])]+=1
            if not nearby: row['status']='no_candidate'
            elif len(nearby)>1: row['status']='ambiguous_reference'
            else:
                row['status']='candidate'
                row['reference_id']=nearby[0]['id']
        rows.append(row)
    for row in rows:
        if row['status']=='candidate':
            if claims[(row['camera'],row['frame'],row['reference_id'])]>1:
                row['status']='competing_observation';row['reference_id']=None
            else: row['status']='matched'
    return rows
