from math import isfinite


def compute_license_checksum(license_key: str, owner: str) -> int:
    """Hash the license text as JavaScript UTF-16 code units."""
    data = f"{license_key}:{owner}:enterprise-v4".encode("utf-16-le", "surrogatepass")
    checksum = 0x811C9DC5
    for offset in range(0, len(data), 2):
        code_unit = data[offset] | (data[offset + 1] << 8)
        checksum = ((checksum ^ code_unit) * 0x01000193) & 0xFFFFFFFF
    return checksum


def validate_enterprise_license(
    license_key: str, owner: str, expected_checksum: int | float
) -> dict[str, bool | str | int]:
    """Validate a string key and owner against a JavaScript numeric checksum."""
    if not license_key.startswith("ENT-"):
        return {"valid": False, "tier": "none"}

    checksum = compute_license_checksum(license_key, owner)
    number = float(expected_checksum)
    expected = (int(number) & 0xFFFFFFFF) if isfinite(number) else 0
    valid = checksum == expected
    return {
        "valid": valid,
        "tier": "enterprise-unlimited" if valid else "invalid",
        "checksum": checksum,
    }
