"""Conservative research hypotheses; no verified global IDs or people counts."""
from collections import defaultdict
import hashlib,json,math,statistics
from numbers import Real

def _finite(value):
    return isinstance(value,Real) and not isinstance(value,bool) and math.isfinite(value)

def build_hypotheses(observations,associations,*,max_spread):
    """Group already-gated local observations using unambiguous supported edges.

    Reject competing edges and whole components containing duplicate cameras.
    A conflicting frame retains all sources but has no fused position. Missing
    frames are never interpolated. Outputs are research hypotheses, not IDs.
    """
    if not _finite(max_spread) or max_spread<=0:raise ValueError('invalid spread')
    nodes=set();by_node=defaultdict(list);seen=set()
    for row in observations:
        camera,ident,frame,x,y=(row[k] for k in ('camera','id','frame','x','y'))
        if not isinstance(camera,str) or not camera.strip() or type(ident) is not int or ident<0 or type(frame) is not int or frame<0 or not _finite(x) or not _finite(y) or (camera,ident,frame) in seen:raise ValueError('invalid observation')
        seen.add((camera,ident,frame));node=(camera,ident);nodes.add(node);by_node[node].append((frame,float(x),float(y)))
    edges=[];seen_edges=set();neighbors=defaultdict(lambda:defaultdict(set))
    for edge in associations:
        a=(edge['left_camera'],edge['left_id']);b=(edge['right_camera'],edge['right_id']);supported=edge['supported']
        if a not in nodes or b not in nodes or a[0]==b[0] or type(supported) is not bool:raise ValueError('invalid association')
        a,b=sorted((a,b));key=(a,b)
        if key in seen_edges:raise ValueError('duplicate association')
        seen_edges.add(key);edges.append((a,b,supported))
        if supported:neighbors[a][b[0]].add(b);neighbors[b][a[0]].add(a)
    def competing(a,b):return len(neighbors[a][b[0]])>1 or len(neighbors[b][a[0]])>1
    provisional=[(a,b) for a,b,s in edges if s and not competing(a,b)]
    parent={node:node for node in nodes}
    def find(node):
        while parent[node]!=node:parent[node]=parent[parent[node]];node=parent[node]
        return node
    def union(a,b):
        x,y=find(a),find(b)
        if x!=y:parent[max(x,y)]=min(x,y)
    for a,b in provisional:union(a,b)
    components=defaultdict(list)
    for node in nodes:components[find(node)].append(node)
    bad=set()
    for component in components.values():
        if len({n[0] for n in component})!=len(component):bad.update(component)
    parent={node:node for node in nodes}
    statuses=[]
    for a,b,s in edges:
        status='unsupported' if not s else 'ambiguous' if competing(a,b) or a in bad or b in bad else 'research_supported'
        if status=='research_supported':union(a,b)
        statuses.append({'left_camera':a[0],'left_id':a[1],'right_camera':b[0],'right_id':b[1],'status':status})
    groups=defaultdict(list)
    for node in nodes:groups[find(node)].append(node)
    result=[]
    for component in sorted((sorted(v) for v in groups.values())):
        digest=hashlib.sha256(json.dumps(component,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()[:16];frames=defaultdict(list)
        for camera,ident in component:
            for frame,x,y in by_node[(camera,ident)]:frames[frame].append({'camera':camera,'id':ident,'x':x,'y':y})
        samples=[]
        for frame,points in sorted(frames.items()):
            points.sort(key=lambda r:(r['camera'],r['id']));spread=max((math.hypot(a['x']-b['x'],a['y']-b['y']) for i,a in enumerate(points) for b in points[i+1:]),default=0.)
            good=spread<=max_spread
            samples.append({'frame':frame,'x':statistics.median(p['x'] for p in points) if good else None,'y':statistics.median(p['y'] for p in points) if good else None,'status':'research_candidate' if good else 'spatial_conflict','max_spread':spread,'sources':points})
        result.append({'id':'hyp-'+digest,'members':[{'camera':camera,'id':ident} for camera,ident in component],'samples':samples})
    return {'hypotheses':result,'associations':sorted(statuses,key=lambda e:(e['left_camera'],e['left_id'],e['right_camera'],e['right_id']))}
