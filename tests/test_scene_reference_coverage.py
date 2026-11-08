import unittest
from walkflows.scene_reference_coverage import compare_scene

class SceneReferenceCoverageTests(unittest.TestCase):
 def test_matching_conflicts_and_reference_boundary(self):
  refs={0:[dict(id=1,x=0,y=0),dict(id=2,x=1,y=0)],1:[dict(id=1,x=0,y=0)]}
  hypotheses=[dict(id="a",samples=[dict(frame=0,status="research_candidate",x=.1,y=0),dict(frame=1,status="spatial_conflict",x=None,y=None),dict(frame=2,status="research_candidate",x=0,y=0)]),dict(id="b",samples=[dict(frame=0,status="research_candidate",x=.2,y=0)])]
  r=compare_scene(hypotheses,refs,3,.5)
  self.assertEqual((r["matched"],r["unmatched_predictions"],r["unmatched_reference"],r["conflicts"],r["outside_reference"]),(1,1,2,1,1))
  self.assertEqual(r["frames"][0]["matches"][0]["prediction_id"],"a")
  self.assertEqual(r["frames"][2]["status"],"reference_unavailable")
 def test_duplicate_track_or_frame_rejected(self):
  h=dict(id="a",samples=[dict(frame=0,status="research_candidate",x=0,y=0)]*2)
  with self.assertRaises(ValueError): compare_scene([h],{0:[]},1,.5)
  with self.assertRaises(ValueError): compare_scene([dict(id="a",samples=[])]*2,{0:[]},1,.5)

if __name__=="__main__": unittest.main()
