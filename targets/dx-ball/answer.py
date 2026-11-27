import math


def _int32(value):
    if not math.isfinite(value):
        return 0
    return (int(value) + 0x80000000) % 0x100000000 - 0x80000000


def calculate_sound_pan(paddle_x, ball_x, screen_width):
    center = _int32(float(screen_width)) >> 1
    delta = (float(ball_x) - center) * 18
    weighted = delta + (_int32(float(paddle_x) - center) >> 2)
    if weighted < -10000:
        return -10000
    if weighted > 10000:
        return 10000
    return _int32(weighted)
