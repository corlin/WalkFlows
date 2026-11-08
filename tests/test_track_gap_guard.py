import unittest
from walkflows.track_gap_guard import segment_track

class TrackGapGuardTest(unittest.TestCase):
 def test_splits_large_color_change_only_across_gap(self):
  rows=[{'frame':1,'feature':[1.,0.]},{'frame':2,'feature':[0.,1.]},{'frame':5,'feature':[1.,0.]},{'frame':8,'feature':[1.,0.]}]
  self.assertEqual(segment_track(rows,.6),[0,0,1,1])
 def test_missing_gap_appearance_is_uncertain(self):
  rows=[{'frame':1,'feature':None},{'frame':3,'feature':[1.,0.]}]
  self.assertEqual(segment_track(rows,.6),[0,1])
 def test_rejects_out_of_order_or_invalid_histogram(self):
  with self.assertRaises(ValueError):segment_track([{'frame':1,'feature':[1.,0.]},{'frame':1,'feature':[1.,0.]}],.6)
  with self.assertRaises(ValueError):segment_track([{'frame':1,'feature':[-1.,2.]}],.6)
