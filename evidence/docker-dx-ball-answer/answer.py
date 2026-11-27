from math import isfinite


def _to_int32(value: float) -> int:
    if not isfinite(value):
        return 0
    return (int(value) + (1 << 31)) % (1 << 32) - (1 << 31)


def calculate_sound_pan(paddle_x: float, ball_x: float, screen_width: float) -> int:
    """Compute the original signed stereo pan for JavaScript Number inputs."""
    center = _to_int32(float(screen_width)) >> 1
    delta = (float(ball_x) - center) * 18
    weighted = delta + (_to_int32(float(paddle_x) - center) >> 2)
    if weighted < -10000:
        return -10000
    if weighted > 10000:
        return 10000
    return _to_int32(weighted)
