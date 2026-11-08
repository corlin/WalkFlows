import unittest
from walkflows.hybrid_journeys import augment_hypotheses

class HybridJourneyTest(unittest.TestCase):
 def test_fallback_adds_frames_without_changing_membership(self):
  h=[{'id':'h','members':[{'camera':'a','id':1},{'camera':'b','id':2}],'samples':[]}]
  rows=[{'camera':'a','local_id':1,'frame':1,'x':1.,'y':1.,'method':'pose'}, {'camera':'b','local_id':2,'frame':1,'x':1.2,'y':1.,'method':'box_fallback'}, {'camera':'a','local_id':1,'frame':2,'x':1.,'y':1.,'method':'box_fallback'}, {'camera':'a','local_id':3,'frame':3,'x':0.,'y':0.,'method':'pose'}]
  out=augment_hypotheses(h,rows,.5);self.assertEqual(out[0]['id'],'h');self.assertEqual([x['frame'] for x in out[0]['samples']],[1,2]);self.assertEqual(len(out[0]['samples'][0]['sources']),2)
 def test_conflict_keeps_sources_without_fused_position(self):
  h=[{'id':'h','members':[{'camera':'a','id':1},{'camera':'b','id':2}]}]
  rows=[{'camera':'a','local_id':1,'frame':1,'x':0.,'y':0.,'method':'pose'}, {'camera':'b','local_id':2,'frame':1,'x':1.,'y':0.,'method':'box_fallback'}]
  s=augment_hypotheses(h,rows,.5)[0]['samples'][0];self.assertEqual(s['status'],'spatial_conflict');self.assertIsNone(s['x']);self.assertEqual(len(s['sources']),2)
 def test_missing_position_not_added_and_duplicate_rejected(self):
  h=[{'id':'h','members':[{'camera':'a','id':1}]}];r={'camera':'a','local_id':1,'frame':1,'x':None,'y':None,'method':'unresolved'}
  self.assertEqual(augment_hypotheses(h,[r],.5)[0]['samples'],[])
  with self.assertRaises(ValueError):augment_hypotheses(h,[r,r],.5)
 def test_mixed_conflict_can_keep_single_pose_with_explicit_flag(self):
  h=[{'id':'h','members':[{'camera':'a','id':1},{'camera':'b','id':2}]}]
  rows=[{'camera':'a','local_id':1,'frame':1,'x':0.,'y':0.,'method':'pose'}, {'camera':'b','local_id':2,'frame':1,'x':1.,'y':0.,'method':'box_fallback'}]
  s=augment_hypotheses(h,rows,.5,prefer_pose_on_mixed_conflict=True)[0]['samples'][0]
  self.assertEqual(s['status'],'research_candidate');self.assertEqual(s['x'],0.);self.assertEqual(s['degraded_reason'],'mixed_source_conflict');self.assertEqual(len(s['sources']),2);self.assertEqual(s['selected_sources'],[{'camera':'a','id':1}])
