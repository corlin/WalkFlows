import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DirectPoseCliTest(unittest.TestCase):
    def test_camera_help_lists_all_six_calibrated_views(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts/probe_site03_pose_direct.py'), '--help'],
            text=True, capture_output=True, check=True,
        )
        for camera in ('C0001020_v1', 'C0001025_v1', 'C0001029_v2',
                       'C0001053_v5', 'C0001055_v4', 'C0001056_v2'):
            self.assertIn(camera, result.stdout)

    def test_journey_help_offers_explicit_six_camera_mode(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts/evaluate_site03_direct_pose_journeys.py'), '--help'],
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--all-cameras', result.stdout)
