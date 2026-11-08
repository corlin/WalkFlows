import unittest
from walkflows.tracklet_links import propose_links

def row(i,f,x=0):return {'camera':'c','local_id':i,'frame':f,'left':x,'top':0.,'right':x+10,'bottom':10.}
class TrackletLinksTest(unittest.TestCase):
 def test_short_overlap_orders_a_candidate(self):
  rows=[row(1,f) for f in range(0,6)]+[row(2,f) for f in range(3,10)]
  links=propose_links(rows,min_shared=3,max_shared=5,iou_threshold=.6)
  self.assertEqual([(x['from_id'],x['to_id'],x['status']) for x in links],[(1,2,'candidate')])
 def test_long_overlap_and_contained_track_do_not_link(self):
  rows=[row(1,f) for f in range(0,20)]+[row(2,f) for f in range(3,10)]
  self.assertEqual(propose_links(rows,min_shared=3,max_shared=5,iou_threshold=.6),[])
 def test_competing_successors_are_ambiguous(self):
  rows=[row(1,f) for f in range(0,6)]+[row(2,f) for f in range(3,10)]+[row(3,f) for f in range(3,10)]
  links=propose_links(rows,min_shared=3,max_shared=5,iou_threshold=.6)
  self.assertEqual([x['status'] for x in links],['ambiguous','ambiguous'])
