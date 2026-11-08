import unittest
from walkflows.dataset_manifest import parse_manifest

class DatasetManifestTest(unittest.TestCase):
 def test_pinned_git_and_lfs_entries(self):
  source={'sha':'a'*40,'siblings':[{'rfilename':'a/file.json','size':7,'blobId':'b'*40},{'rfilename':'b/video.mp4','size':10,'blobId':'c'*40,'lfs':{'sha256':'d'*64,'size':10}}]}
  entries=parse_manifest(source,'a'*40)
  self.assertEqual([(e['path'],e['kind'],e['digest']) for e in entries],[('a/file.json','git','b'*40),('b/video.mp4','sha256','d'*64)])
 def test_reject_bad_revision_paths_duplicates_and_lfs_size(self):
  entry={'rfilename':'dir/file','size':1,'blobId':'b'*40};source={'sha':'a'*40,'siblings':[entry]}
  with self.assertRaises(ValueError):parse_manifest(source,'c'*40)
  for bad in ('../escape','/absolute','a/../b','a\\b','a//b'):
   with self.subTest(bad=bad),self.assertRaises(ValueError):parse_manifest({'sha':'a'*40,'siblings':[{**entry,'rfilename':bad}]},'a'*40)
  with self.assertRaises(ValueError):parse_manifest({'sha':'a'*40,'siblings':[entry,entry]},'a'*40)
  with self.assertRaises(ValueError):parse_manifest({'sha':'a'*40,'siblings':[{**entry,'lfs':{'sha256':'d'*64,'size':2}}]},'a'*40)

if __name__=='__main__':unittest.main()
