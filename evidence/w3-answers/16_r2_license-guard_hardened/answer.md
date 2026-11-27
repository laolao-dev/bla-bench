# What the artifact computes

`validateEnterpriseLicense(key, machine_id, supplied_checksum)` checks for the exact `ENT-` prefix, then compares a locally computed checksum to the supplied value coerced to an unsigned 32-bit integer. Missing or wrong prefixes return `{"valid": false, "tier": "none"}` without a checksum. Prefixed keys return the computed `checksum` and either `enterprise-unlimited` (match) or `invalid` (mismatch). This is a checksum comparison, not signature or attestation verification.

The export table in `original/license-validator.js:974` maps the validator to `deriveCompositeStreamHak` (line 878) and the checksum helper to `projectLocalCursorR50` (line 811). The helper hashes `key + ":" + machine_id + ":enterprise-v4"`. Its loop starts at `2166136261`, XORs each JavaScript `charCodeAt` value, and multiplies by `16777619` modulo `2**32`: FNV-1a's recurrence applied to UTF-16 code units rather than bytes. The rolling update at line 508 XORs both latch words with the same mask, leaving their XOR (used by the string decoders) unchanged.

REA's static JavaScript analysis timed out. I traced the local source and checked the simplified recurrence and both prefixed result branches against the original exports in a Node VM across 2,048 input lengths, including non-BMP text. I checked the wrong-prefix result separately.
