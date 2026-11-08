import unittest
from dataclasses import replace
from walkflows.quality import Quality, Observation, adapt

class UpstreamObservation:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class QualityTests(unittest.TestCase):

    def q(self, **kwargs):
        return replace(Quality(inside_hull=True, in_scene=True, forward_ray=True), **kwargs)

    def make(self, **kwargs):
        base = dict(camera='a', frame=3, local_id=7, fps=15.0, confidence=0.8, xy=(1.0, 2.0), source_sha256='a' * 64, projection_version='probe-v1', quality=self.q())
        base.update(kwargs)
        return Observation(**base)

    def test_strict_default_blocks_unknown_evidence(self):
        (result, reasons) = adapt(self.make(), UpstreamObservation)
        self.assertIsNone(result)
        self.assertEqual(set(reasons), {'floor_unvalidated', 'foot_visibility_unknown', 'sync_unvalidated'})

    def test_research_requires_uncertainty_and_keeps_local_key(self):
        (result, reasons) = adapt(self.make(), UpstreamObservation, research=True)
        self.assertTrue(result.uncertain)
        self.assertEqual(result.track_key, ('a', 7))
        self.assertEqual(len(reasons), 3)
        (b, _) = adapt(self.make(camera='b'), UpstreamObservation, research=True)
        self.assertNotEqual(result.track_key, b.track_key)

    def test_verified_evidence_can_reach_upstream(self):
        q = self.q(floor_validated=True, foot_visibility='visible', sync_validated=True)
        (result, reasons) = adapt(self.make(quality=q), UpstreamObservation)
        self.assertEqual(reasons, ())
        self.assertFalse(result.uncertain)
        self.assertEqual(result.xy, (1.0, 2.0))

    def test_research_never_bypasses_geometry_or_duplicate_gates(self):
        for (q, reason) in [(self.q(inside_hull=False), 'outside_calibration_hull'), (self.q(in_scene=False), 'outside_scene_bounds'), (self.q(forward_ray=False), 'invalid_ray'), (self.q(duplicate_candidate=True), 'local_duplicate_candidate')]:
            (result, reasons) = adapt(self.make(quality=q), UpstreamObservation, research=True)
            self.assertIsNone(result)
            self.assertIn(reason, reasons)

    def test_occluded_is_explicit_and_stays_uncertain(self):
        o = self.make(quality=self.q(foot_visibility='occluded'))
        (result, reasons) = adapt(o, UpstreamObservation, research=True)
        self.assertTrue(result.uncertain)
        self.assertIn('foot_occluded', reasons)

    def test_invalid_numeric_or_provenance_rejected(self):
        for changes in [dict(xy=(float('nan'), 0)), dict(xy=(0, float('inf'))), dict(confidence=-0.1), dict(confidence=float('nan')), dict(frame=-1), dict(frame=True), dict(local_id=-1), dict(camera=''), dict(local_id=1.5), dict(fps='15'), dict(confidence=None), dict(fps=0), dict(fps=float('inf')), dict(source_sha256=''), dict(projection_version='')]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.make(**changes)

    def test_quality_status_values_are_validated(self):
        with self.assertRaises(ValueError):
            Quality(foot_visibility='probably')
        with self.assertRaises(ValueError):
            Quality(floor_validated='yes')

    def test_immutable_values_and_relative_time(self):
        o = self.make()
        self.assertAlmostEqual(o.timestamp_s, 0.2)
        with self.assertRaises(AttributeError):
            o.camera = 'changed'

    def test_unknown_domain_never_passes_research(self):
        (result, reasons) = adapt(self.make(quality=Quality()), UpstreamObservation, research=True)
        self.assertIsNone(result)
        self.assertIn('calibration_domain_unknown', reasons)

    def test_copies_mutable_xy_and_blocks_factory_side_effects(self):
        xy = [1.0, 2.0]
        o = self.make(xy=xy)
        xy[0] = 99
        self.assertEqual(o.xy, (1.0, 2.0))

        def forbidden(**kwargs):
            raise AssertionError('blocked input reached factory')
        (value, _) = adapt(o, forbidden)
        self.assertIsNone(value)

    def test_each_unknown_geometry_gate_is_individually_blocking(self):
        for field, reason in [('inside_hull', 'calibration_domain_unknown'), ('in_scene', 'scene_domain_unknown'), ('forward_ray', 'ray_validity_unknown')]:
            with self.subTest(field=field):
                value,reasons=adapt(self.make(quality=self.q(**{field:None})),UpstreamObservation,research=True)
                self.assertIsNone(value)
                self.assertIn(reason,reasons)
