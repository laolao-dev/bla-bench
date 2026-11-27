import math


def _int32(value):
    if not math.isfinite(value):
        return 0
    low_bits = math.trunc(value) & 0xFFFFFFFF
    return low_bits - 0x100000000 if low_bits >= 0x80000000 else low_bits


def clamp_pan(value):
    """Clamp a numeric pan value and return a signed integer."""
    if value < -10000:
        return -10000
    if value > 10000:
        return 10000
    return _int32(value)


def calculate_sound_pan(ball_x, paddle_x, width):
    """Compute stereo pan from the ball, paddle, and playfield width."""
    center = _int32(float(width)) >> 1
    ball_offset = _int32(float(ball_x) - center) >> 2
    return clamp_pan((float(paddle_x) - center) * 18 + ball_offset)


calculateSoundPan = calculate_sound_pan
clampPan = clamp_pan
