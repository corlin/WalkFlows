from unittest import TestCase
from walkflows.journeys import build_hypotheses

def obs(camera,ident,frame,x):return {'camera':camera,'id':ident,'frame':frame,'x':x,'y':0.0}
def edge(a,ai,b,bi,supported=True):return {'left_camera':a,'left_id':ai,'right_camera':b,'right_id':bi,'supported':supported}

class HypothesesTest(TestCase):
    def test_supported_pair_retains_sources_and_no_missing_frame_interpolation(self):
        points=[obs('a',1,0,0),obs('b',2,0,.2),obs('a',1,2,0)]
        result=build_hypotheses(points,[edge('a',1,'b',2)],max_spread=.5)
        self.assertEqual(len(result['hypotheses']),1)
        track=result['hypotheses'][0]
        self.assertEqual([p['frame'] for p in track['samples']],[0,2])
        self.assertAlmostEqual(track['samples'][0]['x'],.1)
        self.assertEqual(len(track['samples'][0]['sources']),2)
    def test_competing_tracks_are_not_silently_merged(self):
        points=[obs('a',1,0,0),obs('b',2,0,0),obs('b',3,1,0)]
        result=build_hypotheses(points,[edge('a',1,'b',2),edge('a',1,'b',3)],max_spread=.5)
        self.assertEqual(len(result['hypotheses']),3)
        self.assertTrue(all(e['status']=='ambiguous' for e in result['associations']))
    def test_transitive_multi_view_disagreement_does_not_publish_position(self):
        points=[obs('a',1,0,0),obs('b',2,0,.4),obs('c',3,0,.8)]
        result=build_hypotheses(points,[edge('a',1,'b',2),edge('b',2,'c',3)],max_spread=.5)
        sample=result['hypotheses'][0]['samples'][0]
        self.assertIsNone(sample['x']);self.assertEqual(sample['status'],'spatial_conflict')
    def test_duplicate_keys_and_unknown_edge_fail(self):
        p=obs('a',1,0,0)
        with self.assertRaises(ValueError):build_hypotheses([p,p],[],max_spread=.5)
        with self.assertRaises(ValueError):build_hypotheses([p],[edge('a',1,'b',2)],max_spread=.5)
    def test_transitive_component_with_two_ids_from_same_camera_is_rejected(self):
        points=[obs('a',1,0,0),obs('a',2,1,0),obs('b',1,0,0),obs('c',1,0,0)]
        edges=[edge('a',1,'b',1),edge('b',1,'c',1),edge('a',2,'c',1)]
        result=build_hypotheses(points,edges,max_spread=.5)
        self.assertEqual(len(result['hypotheses']),4)
        self.assertEqual({x['status'] for x in result['associations']},{'ambiguous'})

    def test_unsupported_edge_leaves_tracks_separate(self):
        result=build_hypotheses([obs('a',1,0,0),obs('b',2,0,0)],[edge('a',1,'b',2,False)],max_spread=.5)
        self.assertEqual(len(result['hypotheses']),2)
        self.assertEqual(result['associations'][0]['status'],'unsupported')
