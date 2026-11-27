def computeDigest(left: int, right: int) -> int:
    """Return the WebAssembly i32 result as a signed Python integer."""
    result = ((left ^ right) + 42) & 0xFFFFFFFF
    return result if result < 0x80000000 else result - 0x100000000
