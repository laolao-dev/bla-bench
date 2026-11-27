def main(first: int, second: int) -> int:
    """Return the signed i32 result of the WASM entry point."""
    result = ((first ^ second) + 42) & 0xFFFFFFFF
    return result if result < 0x80000000 else result - 0x100000000
