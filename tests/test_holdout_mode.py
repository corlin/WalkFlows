import subprocess
import sys
import unittest
from pathlib import Path
from walkflows.site03_holdout_mode import resolve_mode

class HoldoutModeTest(unittest.TestCase):
    def test_default_preserves_two_existing_views_and_output(self):
        cameras, folder = resolve_mode(False)
        self.assertEqual(cameras, ('C0001055_v4', 'C0001056_v2'))
        self.assertEqual(folder, 'site03-007-comparison')

    def test_all_camera_mode_is_complete_and_isolated(self):
        cameras, folder = resolve_mode(True)
        self.assertEqual(len(cameras), 6)
        self.assertEqual(len(set(cameras)), 6)
        self.assertIn('C0001020_v1', cameras)
        self.assertIn('C0001056_v2', cameras)
        self.assertEqual(folder, 'site03-007-six-comparison')

    def test_experiment_commands_offer_explicit_six_camera_option(self):
        root = Path(__file__).resolve().parents[1]
        for name in ('compare_site03_holdout.py', 'evaluate_site03_holdout_journeys.py'):
            result = subprocess.run([sys.executable, str(root / 'scripts' / name), '--help'],
                                    text=True, capture_output=True, check=True)
            self.assertIn('--all-cameras', result.stdout)
