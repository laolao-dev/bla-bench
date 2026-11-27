"""Reconstruct the JavaScript exports for string keys and organizations."""

_MASK32 = 0xFFFFFFFF


def compute_license_checksum(license_key: str, organization: str) -> int:
    """Return the unsigned 32-bit checksum used by the validator."""
    payload = f"{license_key}:{organization}:enterprise-v4"
    encoded = payload.encode("utf-16-le", errors="surrogatepass")
    checksum = 2166136261
    for offset in range(0, len(encoded), 2):
        code_unit = encoded[offset] | (encoded[offset + 1] << 8)
        checksum = ((checksum ^ code_unit) * 16777619) & _MASK32
    return checksum


def validate_enterprise_license(
    license_key: str, organization: str, claimed_checksum: int
) -> dict:
    """Return the decision, tier, and checksum when calculated."""
    if not license_key or not license_key.startswith("ENT-"):
        return {"valid": False, "tier": "none"}

    checksum = compute_license_checksum(license_key, organization)
    valid = checksum == (claimed_checksum & _MASK32)
    return {
        "valid": valid,
        "tier": "enterprise-unlimited" if valid else "invalid",
        "checksum": checksum,
    }
