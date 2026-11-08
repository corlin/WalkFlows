"""Select experimental foot position while preserving quality uncertainty."""
import math
from numbers import Real

def select_location(box,pose,*,duplicate,max_disagreement):
    def finite(x):return isinstance(x,Real) and not isinstance(x,bool) and math.isfinite(x)
    if type(duplicate) is not bool or not finite(max_disagreement) or max_disagreement<=0:raise ValueError('invalid selection settings')
    def validate(point):
        if point is None:return None
        if not isinstance(point,dict) or type(point.get('valid')) is not bool:raise ValueError('invalid candidate')
        if point['valid'] and (not finite(point.get('x')) or not finite(point.get('y'))):raise ValueError('invalid candidate coordinates')
        return point if point['valid'] else None
    box=validate(box);pose=validate(pose)
    reasons=['floor_unvalidated','foot_visibility_unknown','sync_unvalidated']
    if duplicate:return {'x':None,'y':None,'method':'excluded','disagreement':None,'research_only':True,'reasons':['local_duplicate_candidate',*reasons]}
    disagreement=math.hypot(box['x']-pose['x'],box['y']-pose['y']) if box and pose else None
    if disagreement is not None and disagreement>max_disagreement:return {'x':None,'y':None,'method':'unresolved_disagreement','disagreement':disagreement,'research_only':True,'reasons':['position_method_disagreement',*reasons]}
    if pose:return {'x':pose['x'],'y':pose['y'],'method':'pose','disagreement':disagreement,'research_only':True,'reasons':reasons}
    if box:return {'x':box['x'],'y':box['y'],'method':'box_fallback','disagreement':None,'research_only':True,'reasons':['pose_unavailable',*reasons]}
    return {'x':None,'y':None,'method':'excluded','disagreement':None,'research_only':True,'reasons':['position_unavailable',*reasons]}
