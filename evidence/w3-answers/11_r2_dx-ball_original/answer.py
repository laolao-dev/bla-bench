from math import isfinite


def _to_int32(value):
    if not isfinite(value):
        return 0
    return (int(value) + 0x80000000) % 0x100000000 - 0x80000000


def clampPan(panValue):
    if panValue < -10000:
        return -10000
    if panValue > 10000:
        return 10000
    return _to_int32(panValue)


def calculateSoundPan(paddleX, ballX, screenWidth):
    """Compute the signed stereo pan for numeric game coordinates."""
    center = _to_int32(float(screenWidth)) >> 1
    delta = (float(ballX) - center) * 18
    weighted = delta + (_to_int32(float(paddleX) - center) >> 2)
    return clampPan(weighted)
