"""Extract calibration camera centers without inferring coverage or occlusion."""
from math import isfinite
from numbers import Real

def extract_anchors(scene):
 if not isinstance(scene,dict) or scene.get('global-transformation')!={'translation':[0,0,0],'rotation':[0,0,0,1],'scale':1}:raise ValueError('unsupported global transform')
 keys=scene.get('bcam-keys');transforms=scene.get('bcam-transforms')
 if not isinstance(keys,list) or not isinstance(transforms,list) or len(keys)!=len(transforms) or any(not isinstance(x,str) or not x.strip() for x in keys) or len(set(keys))!=len(keys):raise ValueError('invalid camera list')
 result=[]
 for camera,transform in zip(keys,transforms,strict=True):
  if not isinstance(camera,str) or not camera.strip() or not isinstance(transform,dict) or transform.get('scale')!=1:raise ValueError('invalid camera transform')
  coords=transform.get('translation')
  if not isinstance(coords,list) or len(coords)!=3 or any(isinstance(x,bool) or not isinstance(x,Real) or not isfinite(x) for x in coords):raise ValueError('invalid camera center')
  result.append({'camera':camera,'x':float(coords[0]),'y':float(coords[1]),'height':float(coords[2])})
 return result
