import unittest
from walkflows.paired_pose_comparison import summarize_pairs
class PairedPoseTest(unittest.TestCase):
 def test_paired_distance_summary(self):
  s=summarize_pairs([(1.,2.),(3.,1.),(2.,2.)]);self.assertEqual(s['paired'],3);self.assertEqual(s['nano_median'],2.);self.assertEqual(s['small_median'],2.);self.assertEqual((s['small_closer'],s['nano_closer'],s['ties']),(1,1,1))
 def test_empty_is_unknown_and_bad_distance_rejected(self):
  s=summarize_pairs([]);self.assertIsNone(s['nano_median']);self.assertIsNone(s['small_median'])
  for pair in [(-1.,0.),(float('nan'),1.),(True,1.)]:
   with self.assertRaises(ValueError):summarize_pairs([pair])
