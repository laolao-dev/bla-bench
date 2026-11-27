"""Python equivalents of the license-validator exports for ordinary JS values."""

import math
from decimal import Decimal


_UNDEFINED = object()
_MASK = 0xFFFFFFFF


def _js_string(value):
    if value is _UNDEFINED:
        return "undefined"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        number = float(value)
        if math.isnan(number):
            return "NaN"
        if math.isinf(number):
            return "Infinity" if number > 0 else "-Infinity"
        if number == 0:
            return "0"
        text = repr(number)
        if 1e-6 <= abs(number) < 1e21:
            text = format(Decimal(text), "f")
            return text.rstrip("0").rstrip(".") if "." in text else text
        mantissa, exponent = text.split("e")
        return f"{mantissa.removesuffix('.0')}e{int(exponent):+d}"
    if isinstance(value, (list, tuple)):
        return ",".join("" if item is None else _js_string(item) for item in value)
    return "[object Object]"


def _uint32(value):
    if value is None or value is _UNDEFINED:
        return 0
    if isinstance(value, (bool, int, float)):
        number = float(value)
    else:
        text = _js_string(value).strip().strip("\ufeff").strip()
        try:
            if text.lower().startswith(("0x", "0o", "0b")):
                number = float(int(text, 0))
            elif "_" not in text and text.isascii():
                number = float(text)
            else:
                return 0
        except ValueError:
            return 0
    return int(number) & _MASK if math.isfinite(number) else 0


def compute_license_checksum(license_key=_UNDEFINED, customer=_UNDEFINED):
    payload = f"{_js_string(license_key)}:{_js_string(customer)}:enterprise-v4"
    units = payload.encode("utf-16-le", errors="surrogatepass")
    checksum = 2166136261
    for offset in range(0, len(units), 2):
        code_unit = units[offset] | (units[offset + 1] << 8)
        checksum = ((checksum ^ code_unit) * 16777619) & _MASK
    return checksum


def validate_enterprise_license(
    license_key=_UNDEFINED, customer=_UNDEFINED, expected_checksum=_UNDEFINED
):
    if isinstance(license_key, str):
        if not license_key.startswith("ENT-"):
            return {"valid": False, "tier": "none"}
    elif (
        license_key is _UNDEFINED
        or license_key is None
        or license_key is False
        or isinstance(license_key, (int, float))
        and (license_key == 0 or math.isnan(license_key))
    ):
        return {"valid": False, "tier": "none"}
    else:
        raise TypeError("license_key.startsWith is not a function")

    checksum = compute_license_checksum(license_key, customer)
    valid = checksum == _uint32(expected_checksum)
    return {
        "valid": valid,
        "tier": "enterprise-unlimited" if valid else "invalid",
        "checksum": checksum,
    }


computeLicenseChecksum = compute_license_checksum
validateEnterpriseLicense = validate_enterprise_license
main = validate_enterprise_license
