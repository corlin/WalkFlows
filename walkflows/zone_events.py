"""Conservative summaries of one already-qualified, camera-scoped trajectory.

Zone changes are candidates bounded by two observations; no identity fusion,
quality gate, geometry validation or boundary hysteresis is performed here.
"""
from dataclasses import dataclass
import math
from numbers import Real

@dataclass(frozen=True)
class Sample:
    frame: int
    time: float
    zone: str | None

@dataclass(frozen=True)
class Segment:
    zone: str | None
    first_frame: int
    last_frame: int
    observed_seconds: float
    start_censored: bool
    end_censored: bool

@dataclass(frozen=True)
class Transition:
    before: str | None
    after: str | None
    earliest: float
    latest: float

@dataclass(frozen=True)
class Summary:
    segments: tuple[Segment, ...]
    transitions: tuple[Transition, ...]
    gaps: tuple[tuple[int, int], ...]

def summarize(samples, *, max_interval_s):
    """Summarize adjacent same-zone observations; gaps censor both sides.

    max_interval_s is an explicit upper bound on a usable sampling interval;
    callers must choose it for their source. None means observed outside all
    configured zones, never a missing or rejected observation.
    """
    if isinstance(max_interval_s, bool) or not isinstance(max_interval_s, Real) or not math.isfinite(max_interval_s) or max_interval_s <= 0:
        raise ValueError('invalid maximum interval')
    segments, transitions, gaps = [], [], []
    previous = first = None
    observed = 0.0
    start_censored = True
    def finish(end_censored):
        segments.append(Segment(first.zone, first.frame, previous.frame, observed, start_censored, end_censored))
    for current in samples:
        if not isinstance(current, Sample) or type(current.frame) is not int or current.frame < 0 or isinstance(current.time, bool) or not isinstance(current.time, Real) or not math.isfinite(current.time) or current.time < 0 or (current.zone is not None and (not isinstance(current.zone, str) or not current.zone.strip())):
            raise ValueError('invalid sample')
        if previous is not None and (current.frame <= previous.frame or current.time <= previous.time):
            raise ValueError('samples must be strictly ordered')
        if previous is None:
            first = current
        elif current.frame != previous.frame + 1 or current.time - previous.time > max_interval_s:
            finish(True)
            gaps.append((previous.frame, current.frame))
            first, observed, start_censored = current, 0.0, True
        elif current.zone != previous.zone:
            finish(False)
            transitions.append(Transition(previous.zone, current.zone, previous.time, current.time))
            first, observed, start_censored = current, 0.0, False
        else:
            observed += current.time - previous.time
        previous = current
    if previous is not None:
        finish(True)
    return Summary(tuple(segments), tuple(transitions), tuple(gaps))
