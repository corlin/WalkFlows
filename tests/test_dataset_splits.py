import unittest
from walkflows.dataset_splits import build_splits

class DatasetSplitTest(unittest.TestCase):
 def test_recordings_from_one_site_never_cross_splits(self):
  entries=[{'path':'testcases/006_site03_tracks/a.mp4','size':4},{'path':'unlabeled/site03_u01/b.mp4','size':5},{'path':'testcases/011_site06_standing/a.mp4','size':6},{'path':'testcases/080_site07_front/a.mp4','size':7},{'path':'calibration/scenes/a.json','size':1}]
  x=build_splits(entries)
  self.assertEqual([v['path'] for v in x['train']],['testcases/006_site03_tracks/a.mp4','unlabeled/site03_u01/b.mp4'])
  self.assertEqual(x['validation'][0]['path'],entries[2]['path']);self.assertEqual(x['test'][0]['path'],entries[3]['path']);self.assertEqual(x['shared'][0]['path'],entries[4]['path'])
 def test_unknown_or_ambiguous_scenario_rejected(self):
  for path in ['testcases/unknown/a.mp4','unlabeled/site99_u/a.mp4','testcases/site02_site07/a.mp4']:
   with self.subTest(path=path),self.assertRaises(ValueError):build_splits([{'path':path,'size':1}])

if __name__=='__main__':unittest.main()
