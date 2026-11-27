def main(left: int, right: int) -> int:
    """Return (left XOR right) + 42 as a signed WebAssembly i32."""
    result = ((left ^ right) + 42) & 0xFFFFFFFF
    return result if result < 0x80000000 else result - 0x100000000
