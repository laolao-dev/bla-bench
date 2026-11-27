def _int32(value: float) -> int:
    if not -float('inf') < value < float('inf'):
        return 0
    return ((int(value) + 0x80000000) & 0xFFFFFFFF) - 0x80000000


def clamp_pan(value: float) -> int:
    """Clamp a numeric pan value and truncate it toward zero."""
    if value < -10_000:
        return -10_000
    if value > 10_000:
        return 10_000
    return _int32(value)


def calculate_sound_pan(horizontal: float, primary_horizontal: float, width: float) -> int:
    """Return the signed stereo pan for two positions and a playfield width."""
    midpoint = _int32(float(width)) >> 1
    primary_offset = (float(primary_horizontal) - midpoint) * 18
    secondary_offset = _int32(float(horizontal) - midpoint) >> 2
    return clamp_pan(primary_offset + secondary_offset)


calculateSoundPan = calculate_sound_pan
clampPan = clamp_pan
