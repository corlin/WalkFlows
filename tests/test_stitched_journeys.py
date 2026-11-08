import unittest
from walkflows.stitched_journeys import stitch

def h(ident,camera,track,points):
 return {'id':ident,'members':[{'camera':camera,'id':track}],'samples':[{'frame':f,'status':'research_candidate','x':x,'y':0.,'sources':[{'camera':camera,'id':track,'x':x,'y':0.}]} for f,x in points]}
class StitchTest(unittest.TestCase):
 def test_unique_link_conserves_source_and_marks_same_camera_overlap(self):
  a=h('a','c',1,[(0,0.),(1,0.)]);b=h('b','c',2,[(1,0.),(2,0.)]);out=stitch([a,b],[{'camera':'c','from_id':1,'to_id':2,'status':'candidate'}],.5)
  self.assertEqual(len(out),1);self.assertEqual([s['frame'] for s in out[0]['samples']],[0,1,2]);self.assertEqual(out[0]['samples'][1]['status'],'spatial_conflict');self.assertEqual(len(out[0]['samples'][1]['sources']),2)
 def test_ambiguous_edge_does_not_merge(self):
  a=h('a','c',1,[(0,0.)]);b=h('b','c',2,[(1,0.)]);out=stitch([a,b],[{'camera':'c','from_id':1,'to_id':2,'status':'ambiguous'}],.5);self.assertEqual(len(out),2)
 def test_cross_camera_disagreement_stays_unknown(self):
  a=h('a','c',1,[(0,0.)]);b=h('b','d',2,[(0,2.)]);link={'camera':'c','from_id':1,'to_id':3,'status':'candidate'}
  # Join through a same-camera member in the second hypothesis.
  b['members'].append({'camera':'c','id':3})
  out=stitch([a,b],[link],.5);self.assertEqual(out[0]['samples'][0]['reason'],'cross_view_spread');self.assertIsNone(out[0]['samples'][0]['x'])
