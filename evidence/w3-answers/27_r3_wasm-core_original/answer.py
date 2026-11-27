def compute_digest(left: int, right: int) -> int:
    """Return the unsigned 32-bit result of the Wasm computeDigest export."""
    return ((left ^ right) + 42) & 0xFFFFFFFF
