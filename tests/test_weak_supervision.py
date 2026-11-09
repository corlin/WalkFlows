import unittest
from walkflows.weak_supervision import unique_position_pairs

class WeakSupervisionTest(unittest.TestCase):
 def test_unique_pairs_only_and_unmatched_not_negatives(self):
  predictions=[{'id':1,'x':0.,'y':0.},{'id':2,'x':3.,'y':0.}]
  references=[{'id':9,'x':.1,'y':0.}]
  pairs=unique_position_pairs(predictions,references,.5)
  self.assertEqual(len(pairs),1);self.assertEqual(pairs[0]['prediction_id'],1);self.assertEqual(pairs[0]['reference_id'],9);self.assertAlmostEqual(pairs[0]['target_x'],.1)
 def test_ambiguous_pair_is_not_assigned(self):
  predictions=[{'id':1,'x':0.,'y':0.},{'id':2,'x':.1,'y':0.}]
  self.assertEqual(unique_position_pairs(predictions,[{'id':9,'x':.05,'y':0.}],.5),[])

if __name__=='__main__':unittest.main()
