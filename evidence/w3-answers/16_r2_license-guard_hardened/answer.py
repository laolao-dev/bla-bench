import math
import re
from decimal import Decimal


_MASK = 0xFFFFFFFF
_UNDEFINED = object()


def _number(value):
    try:
        return float(value)
    except OverflowError:
        return -math.inf if value < 0 else math.inf


def _js_string(value):
    if value is _UNDEFINED:
        return 'undefined'
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        number = _number(value)
        if math.isnan(number):
            return 'NaN'
        if math.isinf(number):
            return '-Infinity' if number < 0 else 'Infinity'
        if not number:
            return '0'
        text = repr(number)
        if 1e-6 <= abs(number) < 1e21:
            fixed = format(Decimal(text), 'f')
            return fixed.rstrip('0').rstrip('.') if '.' in fixed else fixed
        mantissa, exponent = text.split('e')
        return f'{mantissa}e{int(exponent):+d}'
    if isinstance(value, (list, tuple)):
        return ','.join('' if item is None else _js_string(item) for item in value)
    return '[object Object]'


def _uint32(value):
    if value is None or isinstance(value, (bool, int, float)):
        number = _number(0 if value is None else value)
    else:
        text = re.sub(r'^[\s\ufeff]+|[\s\ufeff]+$', '', _js_string(value))
        if re.fullmatch(r'0(?:[xX][0-9a-fA-F]+|[oO][0-7]+|[bB][01]+)', text):
            number = _number(int(text, 0))
        elif re.fullmatch(r'[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', text):
            number = float(text)
        else:
            return 0
    return int(number) & _MASK if math.isfinite(number) else 0


def compute_license_checksum(license_key=_UNDEFINED, machine_id=_UNDEFINED):
    """Compute the unsigned 32-bit checksum over UTF-16 code units."""
    text = f'{_js_string(license_key)}:{_js_string(machine_id)}:enterprise-v4'
    units = text.encode('utf-16-le', errors='surrogatepass')
    checksum = 2166136261
    for offset in range(0, len(units), 2):
        unit = units[offset] | (units[offset + 1] << 8)
        checksum = ((checksum ^ unit) * 16777619) & _MASK
    return checksum


def validate_enterprise_license(license_key=_UNDEFINED, machine_id=_UNDEFINED,
                                supplied_checksum=_UNDEFINED):
    """Validate a license and return the artifact's result fields."""
    if not isinstance(license_key, str):
        if (license_key is _UNDEFINED or license_key is None or license_key is False
                or isinstance(license_key, (int, float))
                and (license_key == 0 or math.isnan(_number(license_key)))):
            return {'valid': False, 'tier': 'none'}
        raise TypeError('license_key.startsWith is not a function')
    if not license_key.startswith('ENT-'):
        return {'valid': False, 'tier': 'none'}
    checksum = compute_license_checksum(license_key, machine_id)
    valid = checksum == _uint32(supplied_checksum)
    return {'valid': valid, 'tier': 'enterprise-unlimited' if valid else 'invalid',
            'checksum': checksum}


computeLicenseChecksum = compute_license_checksum
validateEnterpriseLicense = validate_enterprise_license
