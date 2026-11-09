import hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import fetch_multiview_dataset as fetcher

class DatasetFetchTest(unittest.TestCase):
 def test_timeout_retry_keeps_partial_file(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(fetcher,'DEST',Path(tmp)):
   data=b'abcdef';entry={'path':'videos/test.mp4','size':len(data),'kind':'sha256','digest':hashlib.sha256(data).hexdigest()};calls=[]
   def run(args,**kwargs):
    part=Path(args[args.index('--output')+1]);calls.append(part.read_bytes() if part.exists() else b'')
    if len(calls)==1:part.write_bytes(b'abc')
    else:
     self.assertEqual(part.read_bytes(),b'abc');part.write_bytes(data)
   with patch.object(fetcher.subprocess,'run',side_effect=run):self.assertEqual(fetcher.fetch(entry),'downloaded')
   self.assertEqual(len(calls),2);self.assertEqual((Path(tmp)/entry['path']).read_bytes(),data)

if __name__=='__main__':unittest.main()
