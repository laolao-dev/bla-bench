def compute_digest(left: int, right: int) -> int:
    """Return the result as a signed WebAssembly i32."""
    result = ((left ^ right) + 42) & 0xFFFFFFFF
    return result - 0x100000000 if result >= 0x80000000 else result


computeDigest = compute_digest
