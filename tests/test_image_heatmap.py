from unittest import TestCase
from walkflows.image_heatmap import heatmap

def row(frame, local_id, x, y, status='research_candidate_only'):
    return {'frame': frame, 'local_id': local_id, 'x': x, 'y': y, 'status': status}

class ImageHeatmapTest(TestCase):
    def test_time_uses_only_adjacent_samples_in_same_cell(self):
        rows = [row(0, 1, 1, 1), row(1, 1, 1, 1), row(3, 1, 1, 1), row(4, 1, 9, 9)]
        result = heatmap(rows, width=10, height=10, columns=2, rows=2, fps=2)
        self.assertEqual(result['samples'], [[3, 0], [0, 1]])
        self.assertEqual(result['seconds'], [[0.5, 0], [0, 0]])

    def test_filtering_a_sample_breaks_continuity(self):
        rows = [row(0, 1, 1, 1), row(1, 1, 1, 1, 'hard_excluded'), row(2, 1, 1, 1)]
        self.assertEqual(heatmap(rows, width=10, height=10, columns=1, rows=1, fps=2)['seconds'], [[0]])
        self.assertEqual(heatmap(rows, width=10, height=10, columns=1, rows=1, fps=2, include_excluded=True)['seconds'], [[1.0]])

    def test_reject_duplicate_and_outside(self):
        for data in ([row(0, 1, 1, 1), row(0, 1, 2, 2)], [row(0, 1, 10, 1)]):
            with self.subTest(data=data), self.assertRaises(ValueError): heatmap(data, width=10, height=10, columns=2, rows=2, fps=2)
