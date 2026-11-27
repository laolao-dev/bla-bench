def compute_license_checksum(serial_key: str, product_code: str) -> int:
    """Return the artifact's unsigned 32-bit checksum for two strings."""
    encoded = f"{serial_key}:{product_code}:enterprise-v4".encode(
        "utf-16-le", errors="surrogatepass"
    )
    checksum = 0x811C9DC5
    for low, high in zip(encoded[::2], encoded[1::2]):
        checksum = ((checksum ^ (low | (high << 8))) * 0x01000193) & 0xFFFFFFFF
    return checksum


def validate_enterprise_license(
    serial_key: str | None, product_code: str, expected_checksum: int
) -> dict[str, bool | str | int]:
    """Mirror the wrapper for string keys and integer checksums."""
    if not serial_key or not serial_key.startswith("ENT-"):
        return {"valid": False, "tier": "none"}

    try:
        expected = int(float(expected_checksum)) & 0xFFFFFFFF
    except OverflowError:
        expected = 0
    actual = compute_license_checksum(serial_key, product_code)
    valid = actual == expected
    return {
        "valid": valid,
        "tier": "enterprise-unlimited" if valid else "invalid",
        "checksum": actual,
    }
