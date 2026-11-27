# License validator

The main export checks for an `ENT-` prefix and compares a locally computed 32-bit checksum against the supplied value. It does not verify a signature or contact a server on this path.

- `original/license-validator.js:974` maps `validateEnterpriseLicense` to `deriveCompositeStreamHak` and `computeLicenseChecksum` to `projectLocalCursorR50`.
- The loop at `original/license-validator.js:811` starts at `0x811c9dc5`, XORs each UTF-16 code unit of `key:owner:enterprise-v4`, then multiplies by `0x01000193` modulo `2^32`. This is FNV-1a-style hashing over code units, not UTF-8 bytes.
- The validator at `original/license-validator.js:878` returns `valid: false, tier: "none"` without a checksum for a bad prefix. Otherwise it compares against `expected >>> 0` and includes the computed checksum, with tier `enterprise-unlimited` on a match or `invalid` on a mismatch.

REA's JavaScript application analysis timed out. Direct inspection and isolated Node.js probes of the shipped file confirmed the decoded strings and return values, including matches and mismatches across all 1,024 key-length residues with a non-BMP owner. The ring-buffer updates XOR the same mask into both latch entries, preserving the XOR used by the string decoders. The Python port reproduces return values for string keys and owners and numeric checksums, not internal state updates or general JavaScript coercions.
