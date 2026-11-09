import unittest
import numpy as np
from walkflows.scene_transforms import compose_camera,normalized_bounds

class SceneTransformTests(unittest.TestCase):
 def test_global_after_camera_with_scale(self):
  camera={'translation':[2,1,3],'rotation':[0,0,0,1],'scale':2}
  global_transform={'translation':[.8,1.27,0],'rotation':[0,0,1,0],'scale':1}
  result=compose_camera(camera,global_transform)
  np.testing.assert_allclose(result['translation'],[-1.2,.27,3],atol=1e-12)
  np.testing.assert_allclose(result['rotation'],[0,0,1,0],atol=1e-12)
  self.assertEqual(result['scale'],2)
 def test_rotation_order_is_camera_then_global(self):
  from scipy.spatial.transform import Rotation
  camera={'translation':[0,0,0],'rotation':Rotation.from_euler('x',90,degrees=True).as_quat().tolist(),'scale':1}
  global_transform={'translation':[0,0,0],'rotation':Rotation.from_euler('z',90,degrees=True).as_quat().tolist(),'scale':1}
  composed=compose_camera(camera,global_transform)
  np.testing.assert_allclose(Rotation.from_quat(composed['rotation']).apply([0,1,0]),[0,0,1],atol=1e-12)
 def test_identity_and_reversed_bounds(self):
  t={'translation':[1,2,3],'rotation':[0,0,0,1],'scale':1}
  result=compose_camera(t,{'translation':[0,0,0],'rotation':[0,0,0,1],'scale':1})
  np.testing.assert_allclose(result['translation'],t['translation']);self.assertEqual(normalized_bounds([-3,5,12,-4]),[-3,-4,12,5])
 def test_invalid_inputs_rejected(self):
  with self.assertRaises(ValueError):normalized_bounds([1,1,1,2])
  with self.assertRaises(ValueError):compose_camera({'translation':[0,0,0],'rotation':[0,0,0,0],'scale':1},{'translation':[0,0,0],'rotation':[0,0,0,1],'scale':1})

if __name__=='__main__':unittest.main()
