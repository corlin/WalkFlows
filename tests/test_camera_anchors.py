import unittest
from walkflows.camera_anchors import extract_anchors

class CameraAnchorsTest(unittest.TestCase):
 def test_extract_preserves_positions_and_ids(self):
  scene={'global-transformation':{'translation':[0,0,0],'rotation':[0,0,0,1],'scale':1},'bcam-keys':['c1','c2'],'bcam-transforms':[{'translation':[1.,2.,3.],'scale':1},{'translation':[-1.,0.,4.],'scale':1}]}
  self.assertEqual(extract_anchors(scene),[{'camera':'c1','x':1.,'y':2.,'height':3.},{'camera':'c2','x':-1.,'y':0.,'height':4.}])
 def test_mismatch_duplicate_and_nonidentity_rejected(self):
  base={'global-transformation':{'translation':[0,0,0],'rotation':[0,0,0,1],'scale':1},'bcam-keys':['c'],'bcam-transforms':[]}
  with self.assertRaises(ValueError):extract_anchors(base)
  base['bcam-transforms']=[{'translation':[0,0,1],'scale':1}];base['global-transformation']['translation']=[1,0,0]
  with self.assertRaises(ValueError):extract_anchors(base)
 def test_nonfinite_or_duplicate_is_invalid(self):
  base={'global-transformation':{'translation':[0,0,0],'rotation':[0,0,0,1],'scale':1},'bcam-keys':['c','c'],'bcam-transforms':[{'translation':[0,0,1],'scale':1}]*2}
  with self.assertRaises(ValueError):extract_anchors(base)
  base['bcam-keys']=['c','d'];base['bcam-transforms'][1]={'translation':[float('nan'),0,1],'scale':1}
  with self.assertRaises(ValueError):extract_anchors(base)
