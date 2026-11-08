"""Conservative camera-pair candidates; never constructs global identities."""
from collections import defaultdict
import math,statistics
from numbers import Real

def _number(value):
    return isinstance(value,Real) and not isinstance(value,bool) and math.isfinite(value)

def unique_pairs(left,right,*,max_distance):
    if not _number(max_distance) or max_distance<=0:raise ValueError('invalid distance')
    for group in (left,right):
        seen=set()
        for point in group:
            if not isinstance(point,dict) or type(point.get('id')) is not int or point['id']<0 or point['id'] in seen or not _number(point.get('x')) or not _number(point.get('y')):raise ValueError('invalid point')
            seen.add(point['id'])
    candidates=[];left_count=defaultdict(int);right_count=defaultdict(int)
    for a in left:
        for b in right:
            d=math.hypot(a['x']-b['x'],a['y']-b['y'])
            if d<=max_distance:
                candidates.append((a['id'],b['id'],d));left_count[a['id']]+=1;right_count[b['id']]+=1
    return [{'left_id':a,'right_id':b,'distance':d} for a,b,d in candidates if left_count[a]==1 and right_count[b]==1]

def summarize_pairs(rows,*,min_frames,min_consecutive):
    if type(min_frames) is not int or min_frames<1 or type(min_consecutive) is not int or min_consecutive<1:raise ValueError('invalid support thresholds')
    groups=defaultdict(list);seen=set()
    for row in rows:
        frame,a,b,d=(row[k] for k in ('frame','left_id','right_id','distance'))
        if any(type(x) is not int or x<0 for x in (frame,a,b)) or not _number(d) or d<0 or (frame,a,b) in seen:raise ValueError('invalid pair observation')
        seen.add((frame,a,b));groups[a,b].append((frame,d))
    result=[]
    for (a,b),points in sorted(groups.items()):
        points.sort();longest=current=0;last=None
        for frame,_ in points:
            current=current+1 if last is not None and frame==last+1 else 1
            longest=max(longest,current);last=frame
        result.append({'left_id':a,'right_id':b,'frames':len(points),'first_frame':points[0][0],'last_frame':points[-1][0],'longest_consecutive':longest,'median_distance':statistics.median(d for _,d in points),'supported':len(points)>=min_frames and longest>=min_consecutive})
    return result

def local_duplicate_keys(observations,*,containment):
    """Flag both boxes in same-frame high-containment pairs; heuristic only."""
    if not _number(containment) or not 0<containment<=1:raise ValueError('invalid containment')
    groups=defaultdict(list);seen=set();duplicates=set()
    for row in observations:
        frame,ident,box=(row[k] for k in ('frame','id','box'))
        if type(frame) is not int or frame<0 or type(ident) is not int or ident<0 or (frame,ident) in seen or not isinstance(box,(tuple,list)) or len(box)!=4 or not all(map(_number,box)) or box[0]>=box[2] or box[1]>=box[3]:raise ValueError('invalid box')
        seen.add((frame,ident));groups[frame].append((ident,box))
    for frame,group in groups.items():
        for i,(a,A) in enumerate(group):
            for b,B in group[i+1:]:
                overlap=max(0,min(A[2],B[2])-max(A[0],B[0]))*max(0,min(A[3],B[3])-max(A[1],B[1]))
                small=min((A[2]-A[0])*(A[3]-A[1]),(B[2]-B[0])*(B[3]-B[1]))
                if overlap/small>=containment:duplicates.update(((frame,a),(frame,b)))
    return duplicates
