"""Camera-local, image-space detection coverage; not unique people or floor positions."""
import math
from numbers import Real

def heatmap(observations, *, width, height, columns, rows, fps, include_excluded=False):
    if any(type(v) is not int or v <= 0 for v in (width, height, columns, rows)):
        raise ValueError('invalid grid dimensions')
    if isinstance(fps, bool) or not isinstance(fps, Real) or not math.isfinite(fps) or fps <= 0 or type(include_excluded) is not bool:
        raise ValueError('invalid options')
    samples = [[0 for _ in range(columns)] for _ in range(rows)]
    seconds = [[0.0 for _ in range(columns)] for _ in range(rows)]
    seen = set()
    selected = []
    valid_status = {'research_candidate_only', 'strict_candidate', 'hard_excluded'}
    for item in observations:
        frame, ident, x, y, status = (item[k] for k in ('frame', 'local_id', 'x', 'y', 'status'))
        if type(frame) is not int or frame < 0 or type(ident) is not int or ident < 0 or status not in valid_status:
            raise ValueError('invalid observation')
        if any(isinstance(v, bool) or not isinstance(v, Real) or not math.isfinite(v) for v in (x, y)) or not (0 <= x < width and 0 <= y < height):
            raise ValueError('observation outside image')
        key = (frame, ident)
        if key in seen:
            raise ValueError('duplicate observation')
        seen.add(key)
        if status != 'hard_excluded' or include_excluded:
            selected.append((ident, frame, int(x * columns / width), int(y * rows / height)))
    previous = {}
    for ident, frame, col, row in sorted(selected):
        samples[row][col] += 1
        old = previous.get(ident)
        if old is not None and old == (frame - 1, col, row):
            seconds[row][col] += 1 / fps
        previous[ident] = (frame, col, row)
    return {'samples': samples, 'seconds': seconds, 'selected_observations': len(selected), 'total_observations': len(seen)}
