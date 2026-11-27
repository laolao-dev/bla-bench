from math import isfinite


def _int32(value):
    if not isfinite(value):
        return 0
    return ((int(value) + 0x80000000) & 0xFFFFFFFF) - 0x80000000


def clamp_pan(pan):
    if pan < -10000:
        return -10000
    if pan > 10000:
        return 10000
    return _int32(pan)


def calculate_sound_pan(first_x, second_x, width):
    """Compute the artifact's stereo pan for three JavaScript Number inputs."""
    center = _int32(float(width)) >> 1
    raw_pan = (float(second_x) - center) * 18 + (_int32(float(first_x) - center) >> 2)
    return clamp_pan(raw_pan)
