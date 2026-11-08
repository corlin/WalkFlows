from unittest import TestCase
from walkflows.pose_foot import select_foot

class PoseFootTest(TestCase):
    def test_two_confident_ankles_use_midpoint(self):
        row={'status':'unique','left_x':'10','left_y':'20','left_confidence':'0.8','right_x':'20','right_y':'30','right_confidence':'0.9'}
        self.assertEqual(select_foot(row,threshold=.5,width=100,height=100),(15,25,'both'))
    def test_one_ankle_and_missing_sentinel(self):
        row={'status':'unique','left_x':'0','left_y':'0','left_confidence':'0.9','right_x':'20','right_y':'30','right_confidence':'0.9'}
        self.assertEqual(select_foot(row,threshold=.5,width=100,height=100),(20,30,'right'))
        row['right_confidence']='0.1';self.assertIsNone(select_foot(row,threshold=.5,width=100,height=100))
    def test_unmatched_or_bad_options_do_not_produce_foot(self):
        self.assertIsNone(select_foot({'status':'ambiguous'},threshold=.5,width=100,height=100))
        with self.assertRaises(ValueError):select_foot({},threshold=float('nan'),width=100,height=100)
from unittest import TestCase
from walkflows.pose_foot import compare_view_pairs

class PairedViewTest(TestCase):
    def test_pairing_uses_same_frame_and_reference_on_common_support(self):
        left=[{'frame':1,'reference_id':2,'box_world_x':0,'box_world_y':0,'foot_world_x':1,'foot_world_y':0}, {'frame':2,'reference_id':3,'box_world_x':0,'box_world_y':0,'foot_world_x':1,'foot_world_y':0}]
        right=[{'frame':1,'reference_id':2,'box_world_x':2,'box_world_y':0,'foot_world_x':1.5,'foot_world_y':0}, {'frame':2,'reference_id':4,'box_world_x':0,'box_world_y':0,'foot_world_x':0,'foot_world_y':0}]
        pairs=compare_view_pairs(left,right)
        self.assertEqual(len(pairs),1);self.assertEqual(pairs[0]['box_distance'],2);self.assertEqual(pairs[0]['foot_distance'],0.5)
    def test_duplicate_proxy_pair_is_rejected(self):
        p={'frame':1,'reference_id':1,'box_world_x':0,'box_world_y':0,'foot_world_x':0,'foot_world_y':0}
        with self.assertRaises(ValueError):compare_view_pairs([p,p],[])
