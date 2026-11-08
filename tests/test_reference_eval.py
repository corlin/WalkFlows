from unittest import TestCase
from walkflows.reference_eval import convert_reference, match_positions

class ReferenceEvalTest(TestCase):
    def test_reference_retains_empty_tracks_and_converts_coordinates(self):
        source={'frames':3,'width':10,'height':10,'hist-sz':0.5,'top-left':[-1,2],'frame-duration':0.1,'tracks':[{'id':1,'path':[[2,3,0,0,-1,'W']]},{'id':2,'path':[]}]}
        result=convert_reference(source)
        self.assertEqual(result['empty_track_ids'],[2])
        self.assertEqual(result['by_frame'][0],[{'id':1,'x':0.0,'y':3.5}])
        self.assertEqual(result['by_frame'][1],[])
    def test_duplicate_reference_frame_fails(self):
        source={'frames':2,'width':10,'height':10,'hist-sz':1,'top-left':[0,0],'frame-duration':0.1,'tracks':[{'id':1,'path':[[1,1,0],[2,2,0]]}]}
        with self.assertRaises(ValueError):convert_reference(source)
    def test_matching_maximizes_valid_pairs_not_greedy_nearest(self):
        pred=[{'id':'a','x':0.1,'y':0},{'id':'b','x':-0.4,'y':0}]
        truth=[{'id':1,'x':0,'y':0},{'id':2,'x':0.6,'y':0}]
        matches=match_positions(pred,truth,0.51)
        self.assertEqual({(x['prediction_id'],x['reference_id']) for x in matches},{('a',2),('b',1)})
    def test_matching_empty_and_invalid(self):
        self.assertEqual(match_positions([],[],0.5),[])
        with self.assertRaises(ValueError):match_positions([{'id':'a','x':float('nan'),'y':0}],[],0.5)
        with self.assertRaises(ValueError):match_positions([],[],0)
