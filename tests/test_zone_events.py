from unittest import TestCase
from walkflows.zone_events import Sample, summarize

class ZoneEventsTest(TestCase):
    def test_contiguous_segments_and_bounded_transition(self):
        result = summarize([Sample(0, 0.0, None), Sample(1, 0.5, 'a'), Sample(2, 1.0, 'a'), Sample(3, 1.5, 'b')], max_interval_s=0.75)
        self.assertEqual([(s.zone, s.observed_seconds) for s in result.segments], [(None, 0.0), ('a', 0.5), ('b', 0.0)])
        self.assertEqual([(t.before, t.after, t.earliest, t.latest) for t in result.transitions], [(None, 'a', 0.0, 0.5), ('a', 'b', 1.0, 1.5)])
        self.assertTrue(result.segments[0].start_censored)
        self.assertTrue(result.segments[-1].end_censored)

    def test_gap_does_not_invent_entry_or_dwell(self):
        result = summarize([Sample(0, 0.0, 'a'), Sample(1, 0.5, 'a'), Sample(4, 2.0, 'b'), Sample(5, 2.5, 'b')], max_interval_s=0.75)
        self.assertEqual(len(result.transitions), 0)
        self.assertEqual(result.gaps, ((1, 4),))
        self.assertEqual([x.observed_seconds for x in result.segments], [0.5, 0.5])
        self.assertTrue(result.segments[0].end_censored)
        self.assertTrue(result.segments[1].start_censored)

    def test_reject_bad_samples(self):
        for samples in ([Sample(0, 0, 'a'), Sample(0, 1, 'a')], [Sample(0, 1, 'a'), Sample(1, 1, 'a')], [Sample(0, float('nan'), 'a')], [Sample(-1, 0, 'a')], [Sample(0, 0, '')]):
            with self.subTest(samples=samples), self.assertRaises(ValueError): summarize(samples, max_interval_s=1.0)

    def test_timestamp_gap_censors_even_consecutive_frames(self):
        result = summarize([Sample(0, 0.0, 'a'), Sample(1, 2.0, 'b')], max_interval_s=0.1)
        self.assertEqual(result.gaps, ((0, 1),))
        self.assertEqual(result.transitions, ())
        self.assertEqual(sum(x.observed_seconds for x in result.segments), 0)

    def test_empty_and_invalid_interval(self):
        self.assertEqual(summarize([], max_interval_s=1.0).segments, ())
        with self.assertRaises(ValueError): summarize([], max_interval_s=float('inf'))
