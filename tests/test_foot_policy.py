from unittest import TestCase
from walkflows.foot_policy import select_location

class FootPolicyTest(TestCase):
    def test_prefers_valid_pose_and_reports_box_disagreement(self):
        box={'x':0.0,'y':0.0,'valid':True};pose={'x':.3,'y':0.,'valid':True}
        result=select_location(box,pose,duplicate=False,max_disagreement=.5)
        self.assertEqual(result['method'],'pose');self.assertAlmostEqual(result['disagreement'],.3)
        self.assertTrue(result['research_only'])
    def test_missing_pose_falls_back_without_losing_uncertainty(self):
        result=select_location({'x':1.,'y':2.,'valid':True},None,duplicate=False,max_disagreement=.5)
        self.assertEqual(result['method'],'box_fallback');self.assertEqual(result['reasons'],['pose_unavailable','floor_unvalidated','foot_visibility_unknown','sync_unvalidated'])
    def test_disagreement_or_duplicate_prevents_forced_position(self):
        box={'x':0.,'y':0.,'valid':True};pose={'x':1.,'y':0.,'valid':True}
        self.assertEqual(select_location(box,pose,duplicate=False,max_disagreement=.5)['method'],'unresolved_disagreement')
        self.assertIsNone(select_location(box,pose,duplicate=True,max_disagreement=2)['x'])
    def test_invalid_inputs_do_not_silently_pass(self):
        with self.assertRaises(ValueError):select_location({'x':float('nan'),'y':0,'valid':True},None,duplicate=False,max_disagreement=.5)
        with self.assertRaises(ValueError):select_location(None,None,duplicate=False,max_disagreement=0)
