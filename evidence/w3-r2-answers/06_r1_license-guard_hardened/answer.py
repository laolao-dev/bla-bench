"""Reconstruction of the JavaScript exports for string inputs."""

_UINT32_MASK = 0xFFFFFFFF


def compute_license_checksum(license_key: str, subject: str) -> int:
    """Return the FNV-1a-style checksum over UTF-16 code units."""
    data = f"{license_key}:{subject}:enterprise-v4".encode(
        "utf-16-le", errors="surrogatepass"
    )
    checksum = 2166136261
    for offset in range(0, len(data), 2):
        unit = data[offset] | (data[offset + 1] << 8)
        checksum = ((checksum ^ unit) * 16777619) & _UINT32_MASK
    return checksum


def validate_enterprise_license(
    license_key: str, subject: str, supplied_checksum: int
) -> dict[str, bool | str | int]:
    """Return the same result fields as the JavaScript validator."""
    if not license_key.startswith("ENT-"):
        return {"valid": False, "tier": "none"}

    checksum = compute_license_checksum(license_key, subject)
    valid = checksum == (supplied_checksum & _UINT32_MASK)
    return {
        "valid": valid,
        "tier": "enterprise-unlimited" if valid else "invalid",
        "checksum": checksum,
    }
