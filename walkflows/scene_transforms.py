"""Source-aligned camera transform composition for research geometry."""
import math
from numbers import Real
import numpy as np
from scipy.spatial.transform import Rotation

def _values(values,length):
 if not isinstance(values,(list,tuple)) or len(values)!=length or any(isinstance(x,bool) or not isinstance(x,Real) or not math.isfinite(x) for x in values):raise ValueError('invalid vector')
 return np.asarray(values,dtype=float)

def _transform(value):
 if not isinstance(value,dict):raise ValueError('invalid transform')
 t=_values(value.get('translation'),3);q=_values(value.get('rotation'),4);scale=value.get('scale')
 if isinstance(scale,bool) or not isinstance(scale,Real) or not math.isfinite(scale) or scale<=0 or abs(np.linalg.norm(q)-1)>1e-5:raise ValueError('invalid transform')
 return t,Rotation.from_quat(q),float(scale)

def compose_camera(camera,global_transform):
 """Apply the camera transform first and the scene global transform second."""
 t1,r1,s1=_transform(camera);t2,r2,s2=_transform(global_transform)
 return {'translation':(r2.apply(t1*s2)+t2).tolist(),'rotation':(r2*r1).as_quat().tolist(),'scale':s1*s2}

def normalized_bounds(bounds):
 a=_values(bounds,4);x1,x2=sorted((float(a[0]),float(a[2])));y1,y2=sorted((float(a[1]),float(a[3])))
 if x1==x2 or y1==y2:raise ValueError('empty bounds')
 return [x1,y1,x2,y2]


def scene_global_transform(scene):
    """Match upstream's identity default when the global field is absent."""
    return scene.get("global-transformation", {
        "translation": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": 1
    })
