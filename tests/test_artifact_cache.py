from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import hashlib,json
from walkflows.artifact_cache import cache_valid

class ArtifactCacheTest(TestCase):
    def test_cache_requires_same_contract_and_untampered_files(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);data=root/'result.csv';data.write_bytes(b'frame\n1\n')
            digest=hashlib.sha256(data.read_bytes()).hexdigest();record=root/'run.json'
            record.write_text(json.dumps({'contract':{'version':1},'artifacts':{'result.csv':digest}}))
            self.assertTrue(cache_valid(record,{'version':1},root,('result.csv',)))
            self.assertFalse(cache_valid(record,{'version':2},root,('result.csv',)))
            data.write_bytes(b'changed');self.assertFalse(cache_valid(record,{'version':1},root,('result.csv',)))
    def test_missing_or_invalid_cache_is_a_miss(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'run.json';self.assertFalse(cache_valid(p,{},Path(tmp),('a.csv',)))
            p.write_text('{');self.assertFalse(cache_valid(p,{},Path(tmp),('a.csv',)))
from walkflows.artifact_cache import adopt_verified_part

class ResumableDownloadTest(TestCase):
    def test_completed_partial_is_adopted_without_network_and_invalid_never_replaces_destination(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);part=root/'x.download';dest=root/'x';dest.write_bytes(b'old');part.write_bytes(b'bad')
            validator=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()==hashlib.sha256(b'good').hexdigest()
            self.assertFalse(adopt_verified_part(part,dest,validator));self.assertEqual(dest.read_bytes(),b'old')
            part.write_bytes(b'good');self.assertTrue(adopt_verified_part(part,dest,validator));self.assertEqual(dest.read_bytes(),b'good');self.assertFalse(part.exists())
