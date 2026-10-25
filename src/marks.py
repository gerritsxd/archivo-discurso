"""Second at which a character position of a turn's text was spoken (turn["marks"] from process.py)."""
import bisect


def time_at(marks, pos, default):
    """marks: [[char offset, second], ...] sorted by offset. Falls back to `default` (the turn start)."""
    if not marks:
        return default
    i = bisect.bisect_right([m[0] for m in marks], max(0, pos)) - 1
    return marks[max(i, 0)][1]
