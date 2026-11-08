from pathlib import Path
import csv,json,unittest

ROOT=Path(__file__).resolve().parents[1]/'data/processed'

class HybridArtifactTest(unittest.TestCase):
    def test_site02_fallback_preserves_identity_and_original_coordinates(self):
        paths=[ROOT/'site02-quality/observations.jsonl',ROOT/'site02-hybrid-foot/observations.jsonl']
        if not all(p.exists() for p in paths):self.skipTest('site02 research artifacts not available')
        source=[json.loads(s) for s in paths[0].read_text().splitlines()];result=[json.loads(s) for s in paths[1].read_text().splitlines()]
        key=lambda r:(r['camera'],r['frame'],r['local_id']);original={key(r):r for r in source}
        self.assertEqual(len(original),len(source));self.assertEqual({key(r) for r in result},set(original));self.assertEqual(len(result),len(source))
        for row in result:
            q=original[key(row)];self.assertTrue(row['research_only']);self.assertFalse(row['strict_candidate']);self.assertIn('floor_unvalidated',row['reasons']);self.assertIn('sync_unvalidated',row['reasons'])
            if q['quality']['duplicate_candidate']:self.assertEqual(row['method'],'excluded')
            if row['method']=='box_fallback':
                self.assertEqual([row['x'],row['y']],q['xy']);self.assertIn('pose_unavailable',row['reasons']);self.assertTrue(row['box_geometry_valid'])
            if row['method'] in ('excluded','unresolved_disagreement'):self.assertIsNone(row['x']);self.assertIsNone(row['y'])
    def test_site03_candidates_conserve_all_observations(self):
        path=ROOT/'site03-hybrid-foot/observations.jsonl';summary=ROOT/'site03-hybrid-foot/summary.json'
        if not path.exists() or not summary.exists():self.skipTest('site03 research artifacts not available')
        rows=[json.loads(s) for s in path.read_text().splitlines()];meta=json.loads(summary.read_text());self.assertEqual(len(rows),sum(c['observations'] for c in meta['cameras']))
        self.assertEqual(len({(r['camera'],r['frame'],r['local_id']) for r in rows}),len(rows))
        self.assertTrue(all(r['research_only'] and not r['strict_candidate'] for r in rows))
        self.assertTrue(all(r['x'] is None and r['y'] is None for r in rows if r['method'] in ('excluded','unresolved_disagreement')))
        boxes={}
        for cam in meta['cameras']:
            with (ROOT/'site03-floor-probe'/(cam['camera']+'_experimental_floor.csv')).open() as f:
                for r in csv.DictReader(f):boxes[(cam['camera'],int(r['frame']),int(r['local_id']))]=r
        for r in rows:
            if r['method']=='box_fallback':
                box=boxes[(r['camera'],r['frame'],r['local_id'])]
                self.assertEqual([r['x'],r['y']],[float(box['experimental_x']),float(box['experimental_y'])])
                self.assertIn('pose_unavailable',r['reasons'])
