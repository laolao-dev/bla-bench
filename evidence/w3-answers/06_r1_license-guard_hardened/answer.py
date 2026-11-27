import math
import re
from decimal import Decimal


_MASK32 = 0xFFFFFFFF
_UNDEFINED = object()
_JS_WHITESPACE = ('\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004'
                  '\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff')


def _number(value):
    try:
        return float(value)
    except OverflowError:
        return math.inf if value > 0 else -math.inf


def _js_string(value):
    if isinstance(value, str):
        return value
    if value is _UNDEFINED:
        return 'undefined'
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        number = _number(value)
        if math.isnan(number):
            return 'NaN'
        if math.isinf(number):
            return 'Infinity' if number > 0 else '-Infinity'
        if not number:
            return '0'
        text = repr(number)
        if 1e-6 <= abs(number) < 1e21:
            return format(Decimal(text), 'f').removesuffix('.0')
        mantissa, exponent = text.split('e')
        return f'{mantissa.removesuffix(".0")}e{int(exponent):+d}'
    raise TypeError('expected a JavaScript scalar equivalent')


def _uint32(value):
    if isinstance(value, str):
        text = value.strip(_JS_WHITESPACE)
        if re.fullmatch(r'0(?:[xX][0-9a-fA-F]+|[oO][0-7]+|[bB][01]+)', text):
            value = int(text, 0)
        elif re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', text):
            value = float(text)
        else:
            return 0
    if value is None or value is _UNDEFINED:
        return 0
    number = _number(value)
    return math.trunc(number) & _MASK32 if math.isfinite(number) else 0


def compute_license_checksum(license_key=_UNDEFINED, customer_id=_UNDEFINED):
    """Return the unsigned checksum over the JS string forms of the inputs."""
    text = f'{_js_string(license_key)}:{_js_string(customer_id)}:enterprise-v4'
    data = text.encode('utf-16-le', errors='surrogatepass')
    checksum = 2166136261
    for offset in range(0, len(data), 2):
        unit = data[offset] | (data[offset + 1] << 8)
        checksum = ((checksum ^ unit) * 16777619) & _MASK32
    return checksum


def validate_enterprise_license(license_key=_UNDEFINED, customer_id=_UNDEFINED,
                                expected_checksum=_UNDEFINED):
    """Return the artifact's validation result for scalar arguments."""
    if not isinstance(license_key, str):
        if (license_key is _UNDEFINED or not license_key
                or isinstance(license_key, float) and math.isnan(license_key)):
            return {'valid': False, 'tier': 'none'}
        raise TypeError('license key has no startsWith method')
    if not license_key.startswith('ENT-'):
        return {'valid': False, 'tier': 'none'}
    checksum = compute_license_checksum(license_key, customer_id)
    valid = checksum == _uint32(expected_checksum)
    return {'valid': valid, 'tier': 'enterprise-unlimited' if valid else 'invalid',
            'checksum': checksum}
