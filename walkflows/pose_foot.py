"""Experimental pose ankle selection; scores are not calibrated visibility."""
import math
from numbers import Real

def select_foot(row,*,threshold,width,height):
    if isinstance(threshold,bool) or not isinstance(threshold,Real) or not math.isfinite(threshold) or not 0<=threshold<=1 or type(width) is not int or width<=0 or type(height) is not int or height<=0:raise ValueError('invalid foot selection options')
    if row.get('status') not in ('unique','ambiguous','no_candidate'):raise ValueError('invalid match status')
    if row['status']!='unique':return None
    usable=[]
    for side in ('left','right'):
        try:x,y,score=(float(row[side+'_'+key]) for key in ('x','y','confidence'))
        except (KeyError,TypeError,ValueError):continue
        if not all(math.isfinite(v) for v in (x,y,score)) or not 0<=score<=1 or score<threshold or not (0<=x<width and 0<=y<height) or (x==0 and y==0):continue
        usable.append((x,y,side))
    if not usable:return None
    if len(usable)==1:return usable[0]
    return ((usable[0][0]+usable[1][0])/2,(usable[0][1]+usable[1][1])/2,'both')

def compare_view_pairs(left,right):
    """Distances between views on matching frame/reference proxy keys only."""
    def index(rows):
        result={}
        for row in rows:
            key=(row['frame'],row['reference_id'])
            if any(type(k) is not int or k<0 for k in key) or key in result:raise ValueError('invalid or duplicated proxy key')
            coordinates=[row[k] for k in ('box_world_x','box_world_y','foot_world_x','foot_world_y')]
            if any(isinstance(v,bool) or not isinstance(v,Real) or not math.isfinite(v) for v in coordinates):raise ValueError('invalid projected position')
            result[key]=coordinates
        return result
    a=index(left);b=index(right);pairs=[]
    for frame,ref in sorted(a.keys()&b.keys()):
        ax,ay,af_x,af_y=a[frame,ref];bx,by,bf_x,bf_y=b[frame,ref]
        pairs.append({'frame':frame,'reference_id':ref,'box_distance':math.hypot(ax-bx,ay-by),'foot_distance':math.hypot(af_x-bf_x,af_y-bf_y)})
    return pairs
