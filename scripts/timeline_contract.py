"""Subtitle display ranges: zero-based frames, one-based inclusive `from`."""
import math


def caption_frames(start, end, fps):
    first = math.ceil(start * fps - 1e-9)
    last = math.ceil(end * fps - 1e-9) - 1
    if last < first:
        raise ValueError('Caption shorter than one display frame; merge caption chunks')
    return first + 1, last
