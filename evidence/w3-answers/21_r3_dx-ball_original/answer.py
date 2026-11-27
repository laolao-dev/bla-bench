from math import isfinite


def _int32(value):
    if not isfinite(value):
        return 0
    return (int(value) + 2**31) % 2**32 - 2**31


def clamp_pan(pan_value):
    if pan_value < -10000:
        return -10000
    if pan_value > 10000:
        return 10000
    return _int32(pan_value)


def calculate_sound_pan(paddle_x, ball_x, screen_width):
    """Compute stereo pan from numeric coordinates and screen width."""
    center = _int32(float(screen_width)) >> 1
    delta = (float(ball_x) - center) * 18
    weighted = delta + (_int32(float(paddle_x) - center) >> 2)
    return clamp_pan(weighted)


calculateSoundPan = calculate_sound_pan
clampPan = clamp_pan
