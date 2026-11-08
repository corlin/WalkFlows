"""Reference coordinates and conditional one-to-one spatial matching.

Unmatched reference points are not false negatives: camera visibility and
annotation completeness are not supplied by this interface.
"""
import math
from numbers import Real
import numpy as np
from scipy.optimize import linear_sum_assignment

def finite(x):
    return isinstance(x,Real) and not isinstance(x,bool) and math.isfinite(x)

def convert_reference(source):
    frames=source['frames'];width=source['width'];height=source['height'];scale=source['hist-sz'];origin=source['top-left'];duration=source['frame-duration'];tracks=source['tracks']
    if any(type(v) is not int or v<=0 for v in (frames,width,height)) or not finite(scale) or scale<=0 or not finite(duration) or duration<=0 or not isinstance(origin,list) or len(origin)!=2 or not all(map(finite,origin)) or not isinstance(tracks,list):raise ValueError('invalid reference metadata')
    by_frame={i:[] for i in range(frames)};empty=[];ids=set()
    for track in tracks:
        ident=track['id'];path=track['path']
        if type(ident) is not int or ident<0 or ident in ids or not isinstance(path,list):raise ValueError('invalid reference track')
        ids.add(ident);seen=set()
        if not path:empty.append(ident)
        for point in path:
            if not isinstance(point,list) or len(point)<3:raise ValueError('invalid reference point')
            x,y,frame=point[:3]
            if not finite(x) or not finite(y) or type(frame) is not int or not 0<=frame<frames or frame in seen:raise ValueError('invalid reference point')
            seen.add(frame);by_frame[frame].append({'id':ident,'x':x*scale+origin[0],'y':y*scale+origin[1]})
    return {'by_frame':by_frame,'empty_track_ids':empty,'frame_duration':duration,'track_count':len(tracks)}

def match_positions(predictions,references,threshold):
    if not finite(threshold) or threshold<=0:raise ValueError('invalid distance threshold')
    for group in (predictions,references):
        ids=set()
        for point in group:
            if not isinstance(point,dict) or not finite(point.get('x')) or not finite(point.get('y')) or 'id' not in point:raise ValueError('invalid position')
            try:
                if point['id'] in ids:raise ValueError('duplicate id')
                ids.add(point['id'])
            except TypeError as e:raise ValueError('invalid id') from e
    if not predictions or not references:return []
    n=len(predictions);m=len(references);penalty=(n+1)*(threshold+1)
    costs=np.full((n,m+n),penalty,dtype=float);distances=np.empty((n,m))
    for i,p in enumerate(predictions):
        for j,r in enumerate(references):
            distance=math.hypot(p['x']-r['x'],p['y']-r['y']);distances[i,j]=distance
            costs[i,j]=distance if distance<=threshold else 2*penalty
    indices=linear_sum_assignment(costs)
    return [{'prediction_id':predictions[i]['id'],'reference_id':references[j]['id'],'distance':float(distances[i,j])} for i,j in zip(*indices) if j<m and distances[i,j]<=threshold]
