import unittest
from walkflows.association_review import review_events

class AssociationReviewTest(unittest.TestCase):
 def test_event_includes_all_source_context_and_not_duplicate_frames(self):
  h=[{'id':'a','samples':[{'frame':5,'sources':[{'camera':'c1','id':1}]}]},{'id':'b','samples':[{'frame':5,'sources':[{'camera':'c2','id':2},{'camera':'c3','id':3}]}]}]
  s={'results':[{'radius':.5,'same_reference_multiple_hypothesis_frames':1,'same_reference_multiple_hypothesis_examples':[{'frame':5,'reference_id':9,'hypotheses':['a','b']}]}]}
  x=review_events(s,h);self.assertEqual(x[0]['frame'],5);self.assertEqual([z['camera'] for z in x[0]['sources']],['c1','c2','c3']);self.assertEqual(x[0]['reference_id'],9)
 def test_missing_hypothesis_or_frame_is_rejected(self):
  s={'results':[{'radius':.5,'same_reference_multiple_hypothesis_frames':1,'same_reference_multiple_hypothesis_examples':[{'frame':5,'reference_id':9,'hypotheses':['a','missing']}]}]}
  with self.assertRaises(ValueError):review_events(s,[{'id':'a','samples':[{'frame':5,'sources':[{'camera':'c1','id':1}]}]}])
