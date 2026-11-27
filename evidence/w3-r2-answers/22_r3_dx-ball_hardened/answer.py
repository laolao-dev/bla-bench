from math import isfinite


def _int32(value):
    if not isfinite(value):
        return 0
    return (int(value) + 2**31) % 2**32 - 2**31


def clamp_pan(pan):
    """Clamp a numeric pan to the game's range and truncate toward zero."""
    if pan < -10000:
        return -10000
    if pan > 10000:
        return 10000
    return _int32(pan)


def calculate_sound_pan(ball_x, paddle_x, field_width):
    """Compute the DX-Ball stereo pan from horizontal coordinates."""
    center = _int32(float(field_width)) >> 1
    raw_pan = (float(paddle_x) - center) * 18 + (_int32(float(ball_x) - center) >> 2)
    return clamp_pan(raw_pan)
