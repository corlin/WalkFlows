import unittest
from walkflows.tracker_comparison import compare

def box(ident,frame=0,x=0):
 return {'local_id':ident,'frame':frame,'left':x,'top':0,'right':x+10,'bottom':10}

class TrackerComparisonTest(unittest.TestCase):
 def test_one_to_one_matching_and_missing(self):
  result=compare([box(1),box(2,1)],[box(5),box(7,2)],.8)
  self.assertEqual(result['pairs'],[{'left_id':1,'right_id':5,'frames':1}])
  self.assertEqual(result['left_status'],{'unique':1,'no_candidate':1})
  self.assertEqual(result['right_status'],{'unique':1,'no_candidate':1})
 def test_competition_is_not_counted_as_unique(self):
  result=compare([box(1),box(2)],[box(5)],.8)
  self.assertEqual(result['pairs'],[])
  self.assertEqual(result['left_status'],{'ambiguous':2})
  self.assertEqual(result['right_status'],{'ambiguous':1})
