from math import isfinite


def _int32(value):
    if not isfinite(value):
        return 0
    bits = int(value) & 0xFFFFFFFF
    return bits - 0x100000000 if bits >= 0x80000000 else bits


def clamp_pan(pan_value):
    """Clamp a JavaScript numeric pan value and truncate toward zero."""
    if pan_value < -10000:
        return -10000
    if pan_value > 10000:
        return 10000
    return _int32(pan_value)


def calculate_sound_pan(paddle_x, ball_x, screen_width):
    """Return the signed stereo pan for numeric coordinates and screen width."""
    center = _int32(float(screen_width)) >> 1
    delta = (float(ball_x) - center) * 18
    weighted = delta + (_int32(float(paddle_x) - center) >> 2)
    return clamp_pan(weighted)
