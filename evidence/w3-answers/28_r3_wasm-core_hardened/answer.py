def main(first: int, second: int) -> int:
    """Return the WASM result as a signed 32-bit integer."""
    result = ((first ^ second) + 42) & 0xFFFFFFFF
    return result if result < 0x80000000 else result - 0x100000000
