from unittest import TestCase
from walkflows.crossview import unique_pairs, summarize_pairs

class CrossviewTest(TestCase):
    def test_one_to_one_candidate_requires_unique_neighborhood_on_both_sides(self):
        left=[{'id':1,'x':0.0,'y':0.0},{'id':2,'x':0.2,'y':0.0}]
        right=[{'id':3,'x':0.1,'y':0.0}]
        self.assertEqual(unique_pairs(left,right,max_distance=0.3),[])
        self.assertEqual(unique_pairs([left[0]],right,max_distance=0.3)[0]['left_id'],1)
    def test_track_evidence_uses_consecutive_frames_and_does_not_bridge_gaps(self):
        rows=[{'frame':f,'left_id':1,'right_id':2,'distance':0.1} for f in (0,1,2,5,6)]
        summary=summarize_pairs(rows,min_frames=5,min_consecutive=4)
        self.assertEqual(summary[0]['longest_consecutive'],3)
        self.assertFalse(summary[0]['supported'])
        self.assertTrue(summarize_pairs(rows,min_frames=5,min_consecutive=3)[0]['supported'])
    def test_invalid_or_duplicate_observations_are_rejected(self):
        p={'id':1,'x':0,'y':0}
        with self.assertRaises(ValueError):unique_pairs([p,p],[],max_distance=1)
        with self.assertRaises(ValueError):unique_pairs([],[],max_distance=0)
        with self.assertRaises(ValueError):summarize_pairs([{'frame':0,'left_id':1,'right_id':2,'distance':0.1}]*2,min_frames=1,min_consecutive=1)
from unittest import TestCase
from walkflows.crossview import local_duplicate_keys

class DuplicateEvidenceTest(TestCase):
    def test_containment_flags_both_on_same_frame_only(self):
        rows=[{'frame':0,'id':1,'box':(0,0,10,10)},{'frame':0,'id':2,'box':(1,1,9,9)},{'frame':1,'id':3,'box':(1,1,9,9)}]
        self.assertEqual(local_duplicate_keys(rows,containment=0.9),{(0,1),(0,2)})
    def test_invalid_box_rejected(self):
        with self.assertRaises(ValueError):local_duplicate_keys([{'frame':0,'id':1,'box':(1,1,1,2)}],containment=.9)
