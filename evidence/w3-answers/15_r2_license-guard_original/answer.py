def compute_license_checksum(serial_key: str, product_code: str) -> int:
    combined = f"{serial_key}:{product_code}:enterprise-v4"
    units = combined.encode("utf-16-le", errors="surrogatepass")
    checksum = 0x811C9DC5
    for offset in range(0, len(units), 2):
        code_unit = units[offset] | (units[offset + 1] << 8)
        checksum = ((checksum ^ code_unit) * 0x01000193) & 0xFFFFFFFF
    return checksum


def validate_enterprise_license(
    serial_key: str | None, product_code: str, expected_checksum: int
) -> dict[str, bool | str | int]:
    if not serial_key or not serial_key.startswith("ENT-"):
        return {"valid": False, "tier": "none"}
    actual = compute_license_checksum(serial_key, product_code)
    valid = actual == (expected_checksum & 0xFFFFFFFF)
    return {
        "valid": valid,
        "tier": "enterprise-unlimited" if valid else "invalid",
        "checksum": actual,
    }
