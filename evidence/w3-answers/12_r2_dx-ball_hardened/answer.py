import math


def _int32(value):
    if not math.isfinite(value):
        return 0
    bits = int(value) & 0xFFFFFFFF
    return bits - 0x100000000 if bits >= 0x80000000 else bits


def clamp_pan(value):
    """Clamp a numeric pan value and truncate toward zero."""
    value = float(value)
    if value < -10000:
        return -10000
    if value > 10000:
        return 10000
    return _int32(value)


def calculate_sound_pan(first, second, third):
    """Return the artifact's stereo pan value for three numeric inputs."""
    center = _int32(float(third)) >> 1
    pan = (float(second) - center) * 18 + (_int32(float(first) - center) >> 2)
    return clamp_pan(pan)


calculateSoundPan = calculate_sound_pan
clampPan = clamp_pan
