import math


def _int32(value: float) -> int:
    if not math.isfinite(value):
        return 0
    return (int(value) + 2**31) % 2**32 - 2**31


def calculate_sound_pan(paddle_x: float, ball_x: float, screen_width: float) -> int:
    center = _int32(float(screen_width)) >> 1
    delta = (float(ball_x) - center) * 18
    weighted = delta + (_int32(float(paddle_x) - center) >> 2)
    if weighted < -10000:
        return -10000
    if weighted > 10000:
        return 10000
    return _int32(weighted)
