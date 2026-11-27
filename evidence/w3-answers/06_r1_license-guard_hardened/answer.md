# What the artifact computes

`validateEnterpriseLicense(key, customerId, expected)` checks for the case-sensitive `ENT-` prefix. Without it, the function returns `{valid: false, tier: "none"}` and no checksum. Otherwise it compares the computed checksum with `expected >>> 0` and returns the checksum, a Boolean match result, and the tier `enterprise-unlimited` (match) or `invalid` (mismatch). The other export, `computeLicenseChecksum`, computes the same checksum without checking the prefix.

REA `open_binary` identified `original/license-validator.js` as JavaScript (SHA-256 `9a67d258587e950d3fc5a264f2d6e6aea0fb70c8068b7033a696b16e283325b5`). REA's application analysis timed out, so I traced the local source and compared the port against Node. The export table at line 974 points to the checksum at line 811 and validator at line 878. The checksum builds `key + ":" + customerId + ":enterprise-v4"` and, for each UTF-16 code unit, XORs it into an accumulator initialized to `2166136261`, then multiplies by `16777619` modulo `2**32`. This resembles FNV-1a but uses a different multiplier and processes code units rather than bytes. The state update XORs both latch words with the same value, preserving the XOR used by the string decoder.

The Python port handles scalar arguments, not JavaScript objects with custom coercion or methods.
