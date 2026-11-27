def main(left: int, right: int) -> int:
    """Return the Wasm i32 result as a signed Python integer."""
    result = ((left ^ right) + 42) & 0xFFFFFFFF
    return result - 0x100000000 if result >= 0x80000000 else result
