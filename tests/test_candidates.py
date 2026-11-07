import unittest

from walkflows.candidates import candidates_at_frame


class CandidateTests(unittest.TestCase):
    def test_uses_same_frame_and_rejects_distant_points(self):
        left = [{"frame": 25, "local_id": 1, "world_x": 0, "world_y": 0}]
        right = [
            {"frame": 25, "local_id": 2, "world_x": 0.3, "world_y": 0.4},
            {"frame": 25, "local_id": 3, "world_x": 2, "world_y": 0},
            {"frame": 26, "local_id": 4, "world_x": 0, "world_y": 0},
        ]
        pairs = candidates_at_frame(left, right, max_distance=1)
        self.assertEqual([(p["left_id"], p["right_id"]) for p in pairs], [(1, 2)])
        self.assertAlmostEqual(pairs[0]["distance"], 0.5)

    def test_keeps_ambiguous_candidates_without_forced_assignment(self):
        left = [{"frame": 1, "local_id": 1, "world_x": 0, "world_y": 0}]
        right = [{"frame": 1, "local_id": i, "world_x": 0, "world_y": 0} for i in (2, 3)]
        self.assertEqual(len(candidates_at_frame(left, right, max_distance=1)), 2)
