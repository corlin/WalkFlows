"""Research image-to-floor projection with explicit geometric exclusions."""
import cv2
import numpy as np
from scipy.spatial.transform import Rotation
from walkflows.scene_transforms import compose_camera,normalized_bounds

_EXPONENTS=np.array([(d-j,j) for d in range(8,-1,-1) for j in range(d+1)])
_IDENTITY={'translation':[0,0,0],'rotation':[0,0,0,1],'scale':1}

def project_pixel(sensor,camera,pixel,bounds,image_size=(896,672)):
 try:
  size=np.asarray(sensor['format'],dtype=float);center=np.asarray(sensor['center'],dtype=float);factor=float(sensor['scale']);matrix=np.asarray(sensor['A'],dtype=float);hull=np.asarray(sensor['calib-hull'],dtype=np.float32);point=np.asarray(pixel,dtype=float);image=np.asarray(image_size,dtype=float)
 except (KeyError,TypeError,ValueError) as exc:raise ValueError('invalid sensor model') from exc
 if size.shape!=(2,) or center.shape!=(2,) or matrix.shape!=(2,45) or hull.ndim!=2 or hull.shape[1:]!=(2,) or len(hull)<3 or point.shape!=(2,) or image.shape!=(2,) or not all(np.isfinite(x).all() for x in (size,center,matrix,hull,point,image)) or not np.isfinite(factor) or factor<=0 or np.any(size<=0) or np.any(image<=0):raise ValueError('invalid sensor model')
 transform=compose_camera(camera,_IDENTITY);bounds=normalized_bounds(bounds)
 if np.any(point<0) or np.any(point>=image):return None
 sensor_point=point*size/image
 if cv2.pointPolygonTest(hull,tuple(sensor_point),False)<0:return None
 xy=(sensor_point-center)*factor;terms=xy[0]**_EXPONENTS[:,0]*xy[1]**_EXPONENTS[:,1];uv=matrix@terms;ray=Rotation.from_quat(transform['rotation']).apply([*uv,1.]);origin=np.asarray(transform['translation'])
 if not np.isfinite(ray).all() or abs(ray[2])<=1e-8:return None
 distance=-origin[2]/ray[2]
 if not np.isfinite(distance) or distance<=0:return None
 world=origin+distance*ray
 if not np.isfinite(world).all() or not (bounds[0]<=world[0]<=bounds[2] and bounds[1]<=world[1]<=bounds[3]):return None
 return [float(world[0]),float(world[1])]
