"""Conditional clock bounds from authenticated, bounded request samples.

This is a pure calculation. It does not read or change the system clock. A
caller must verify the raw evidence, source clock accuracy, and the assumed
drift bound; absent those facts, the result is not a UTC certificate.
"""
from dataclasses import dataclass
import math
import re

_SHA = re.compile(r"[0-9a-f]{64}\Z")
MAX_RTT_MS = 450
MAX_WALL_MONO_DIFFERENCE_MS = 5
MAX_SAMPLE_AGE_MS = 60_000


@dataclass(frozen=True)
class ClockSample:
    source: str
    start_local_ms: int
    end_local_ms: int
    monotonic_elapsed_ms: int
    server_ms: int
    server_error_ms: int
    evidence_sha256: str


def offset_interval(samples, at_local_ms, drift_bound_ppm):
    """Return (min,max) server-minus-local offset under the stated assumptions.

    Each trusted server timestamp must be generated during its measured request
    and be within server_error_ms of UTC. The supplied drift bound must be
    independently justified for the entire period; a historical estimate alone
    does not prove a future bound. Source/clock failures reject the observation.
    """
    if (isinstance(at_local_ms, bool) or not isinstance(at_local_ms, int)
            or not isinstance(drift_bound_ppm, (int, float)) or isinstance(drift_bound_ppm, bool)
            or not math.isfinite(drift_bound_ppm) or not 0 <= drift_bound_ppm <= 1000):
        raise ValueError("invalid time or drift bound")
    samples = list(samples)
    if len(samples) < 2 or any(not isinstance(s, ClockSample) for s in samples):
        raise ValueError("two independent sources required")
    if len({s.source for s in samples}) != len(samples):
        raise ValueError("duplicate clock source")
    intervals = []
    for s in samples:
        fields = (s.start_local_ms, s.end_local_ms, s.monotonic_elapsed_ms, s.server_ms, s.server_error_ms)
        if (not isinstance(s.source, str) or not s.source
                or any(isinstance(x, bool) or not isinstance(x, int) for x in fields)
                or not isinstance(s.evidence_sha256, str) or not _SHA.fullmatch(s.evidence_sha256)):
            raise ValueError("invalid clock sample or evidence")
        wall = s.end_local_ms - s.start_local_ms
        if (not 0 <= wall <= MAX_RTT_MS or not 0 <= s.monotonic_elapsed_ms <= MAX_RTT_MS
                or abs(wall - s.monotonic_elapsed_ms) > MAX_WALL_MONO_DIFFERENCE_MS):
            raise ValueError("negative, slow, or inconsistent request duration")
        if s.server_error_ms < 0 or not s.end_local_ms <= at_local_ms <= s.end_local_ms + MAX_SAMPLE_AGE_MS:
            raise ValueError("stale sample or invalid server uncertainty")
        drift = math.ceil((at_local_ms - s.start_local_ms) * drift_bound_ppm / 1_000_000)
        intervals.append((s.server_ms - s.server_error_ms - s.end_local_ms - drift,
                          s.server_ms + s.server_error_ms - s.start_local_ms + drift))
    low, high = max(x[0] for x in intervals), min(x[1] for x in intervals)
    if low > high:
        raise ValueError("clock-source intervals disagree")
    return low, high
