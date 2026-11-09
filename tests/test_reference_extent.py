import unittest
from walkflows.reference_extent import normalize_reference_extent

class ReferenceExtentTest(unittest.TestCase):
    def setUp(self):
        self.reference = {'frames': 499, 'frame-duration': 1 / 15,
                          'tracks': [{'id': 1, 'path': [[1, 2, 499]]}]}
        self.videos = [{'frames': 500, 'fps': 15}, {'frames': 500, 'fps': 15}]

    def test_known_scene_boundary_is_extended_without_mutating_source(self):
        fixed, policy = normalize_reference_extent('004_site01_clutter', self.reference, self.videos)
        self.assertEqual(fixed['frames'], 500)
        self.assertEqual(self.reference['frames'], 499)
        self.assertEqual(policy, 'verified_004_inclusive_boundary')

    def test_extension_requires_matching_video_evidence(self):
        for videos in ([], [{'frames': 499, 'fps': 15}], [{'frames': 500, 'fps': 25}]):
            with self.assertRaises(ValueError):
                normalize_reference_extent('004_site01_clutter', self.reference, videos)

    def test_other_scene_is_not_silently_extended(self):
        fixed, policy = normalize_reference_extent('other', self.reference, [])
        self.assertEqual(fixed['frames'], 499)
        self.assertEqual(policy, 'declared_frame_count')
