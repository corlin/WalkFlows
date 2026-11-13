import unittest

from scripts.probe_wildtrack_official import match_counts


class WildtrackProbeTest(unittest.TestCase):
    def test_matches_are_one_to_one_and_respect_threshold(self):
        reference=[[0,0,10,10],[20,20,30,30]]
        self.assertEqual(match_counts([[0,0,10,10],[0,0,10,10]],reference,.5),1)
        self.assertEqual(match_counts([[0,0,10,10],[20,20,30,30]],reference,.5),2)
        self.assertEqual(match_counts([[100,100,110,110]],reference,.5),0)
        self.assertEqual(match_counts([],reference,.5),0)


if __name__=="__main__":
    unittest.main()
