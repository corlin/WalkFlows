"""Explicit local-observation evidence and adapters; no tracking or identity assignment."""
from dataclasses import dataclass
import math
import re
from numbers import Real

@dataclass(frozen=True)
class Quality:
    inside_hull: bool | None = None
    in_scene: bool | None = None
    forward_ray: bool | None = None
    floor_validated: bool = False
    foot_visibility: str = 'unknown'
    sync_validated: bool = False
    duplicate_candidate: bool = False

    def __post_init__(self):
        for name in ('inside_hull', 'in_scene', 'forward_ray'):
            if getattr(self, name) is not None and type(getattr(self, name)) is not bool:
                raise ValueError(name + ' must be bool or None')
        for name in ('floor_validated', 'sync_validated', 'duplicate_candidate'):
            if type(getattr(self, name)) is not bool:
                raise ValueError(name + ' must be bool')
        if self.foot_visibility not in ('unknown', 'visible', 'occluded'):
            raise ValueError('invalid foot visibility')

    def reasons(self):
        result = []
        for (value, negative, unknown) in [(self.inside_hull, 'outside_calibration_hull', 'calibration_domain_unknown'), (self.in_scene, 'outside_scene_bounds', 'scene_domain_unknown'), (self.forward_ray, 'invalid_ray', 'ray_validity_unknown')]:
            if value is not True:
                result.append(negative if value is False else unknown)
        if self.duplicate_candidate:
            result.append('local_duplicate_candidate')
        if not self.floor_validated:
            result.append('floor_unvalidated')
        if self.foot_visibility != 'visible':
            result.append('foot_occluded' if self.foot_visibility == 'occluded' else 'foot_visibility_unknown')
        if not self.sync_validated:
            result.append('sync_unvalidated')
        return tuple(result)

    @property
    def hard_blocked(self):
        return self.inside_hull is not True or self.in_scene is not True or self.forward_ray is not True or self.duplicate_candidate

@dataclass(frozen=True)
class Observation:
    camera: str
    frame: int
    local_id: int
    fps: float
    confidence: float
    xy: tuple[float, float]
    source_sha256: str
    projection_version: str
    quality: Quality

    def __post_init__(self):
        if not isinstance(self.camera, str) or not self.camera.strip():
            raise ValueError('camera required')
        for name in ('frame', 'local_id'):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(name + ' must be nonnegative int')
        if not isinstance(self.fps, Real) or isinstance(self.fps, bool) or (not math.isfinite(self.fps)) or (self.fps <= 0):
            raise ValueError('invalid fps')
        if not isinstance(self.confidence, Real) or isinstance(self.confidence, bool) or (not math.isfinite(self.confidence)) or (not 0 <= self.confidence <= 1):
            raise ValueError('invalid confidence')
        try:
            xy = tuple(self.xy)
            if len(xy) != 2 or any((isinstance(v, bool) or not math.isfinite(v) for v in xy)):
                raise ValueError('invalid xy')
        except TypeError as error:
            raise ValueError('invalid xy') from error
        object.__setattr__(self, 'xy', xy)
        if not isinstance(self.source_sha256, str) or re.fullmatch('[0-9a-f]{64}', self.source_sha256) is None:
            raise ValueError('source SHA256 required')
        if not isinstance(self.projection_version, str) or not self.projection_version.strip():
            raise ValueError('projection version required')
        if not isinstance(self.quality, Quality):
            raise ValueError('quality evidence required')

    @property
    def timestamp_s(self):
        return self.frame / self.fps

def adapt(observation, observation_type, *, research=False, index=0):
    """Return upstream observation and evidence reasons, or None if gated out.

    Research mode permits unvalidated physical/visibility/sync assumptions only.
    It cannot bypass unknown/invalid geometry or duplicate candidates. No global
    ID is created. Camera-scoped track_key is preserved.
    """
    if type(research) is not bool:
        raise ValueError('research must be bool')
    if type(index) is not int or index < 0:
        raise ValueError('index must be nonnegative int')
    reasons = observation.quality.reasons()
    if observation.quality.hard_blocked or (reasons and (not research)):
        return (None, reasons)
    upstream = observation_type(camera_id=observation.camera, index=index, xy=observation.xy, confidence=observation.confidence, uncertain=bool(reasons), track_key=(observation.camera, observation.local_id))
    return (upstream, reasons)
