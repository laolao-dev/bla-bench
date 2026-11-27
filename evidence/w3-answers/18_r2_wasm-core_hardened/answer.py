def main(left: int, right: int) -> int:
    """Return the signed WebAssembly i32 result of (left XOR right) + 42."""
    result = ((left ^ right) + 42) & 0xFFFFFFFF
    return result if result < 0x80000000 else result - 0x100000000
