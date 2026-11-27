import math


def _int32(value):
    if not math.isfinite(value):
        return 0
    return ((int(value) + (1 << 31)) % (1 << 32)) - (1 << 31)


def calculate_sound_pan(x, sound_x, width):
    """Compute the artifact's integer stereo pan for numeric inputs."""
    center = _int32(float(width)) >> 1
    pan = (float(sound_x) - center) * 18 + (_int32(float(x) - center) >> 2)
    if pan < -10000:
        return -10000
    if pan > 10000:
        return 10000
    return _int32(pan)


calculateSoundPan = calculate_sound_pan
