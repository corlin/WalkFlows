import unittest
import numpy as np
from walkflows.floor_projection import project_pixel

class FloorProjectionTest(unittest.TestCase):
 def setUp(self):
  self.sensor={'format':[896,672],'center':[0,0],'scale':1,'A':[[0]*45,[0]*45],'calib-hull':[[0,0],[896,0],[896,672],[0,672]]}
  self.sensor['A'][0][-3]=1;self.sensor['A'][1][-2]=1
  self.camera={'translation':[0,0,2],'rotation':[1,0,0,0],'scale':1}
 def test_principal_ray_hits_ground(self):
  point=project_pixel(self.sensor,self.camera,[0,0],[-10,-10,10,10])
  np.testing.assert_allclose(point,[0,0],atol=1e-12)
 def test_outside_hull_and_nonforward_are_unknown(self):
  self.assertIsNone(project_pixel(self.sensor,self.camera,[-1,0],[-10,-10,10,10]))
  camera={'translation':[0,0,2],'rotation':[0,0,0,1],'scale':1}
  self.assertIsNone(project_pixel(self.sensor,camera,[0,0],[-10,-10,10,10]))
 def test_invalid_model_rejected(self):
  sensor={**self.sensor,'A':[[0]*3,[0]*3]}
  with self.assertRaises(ValueError):project_pixel(sensor,self.camera,[0,0],[-10,-10,10,10])

if __name__=='__main__':unittest.main()
