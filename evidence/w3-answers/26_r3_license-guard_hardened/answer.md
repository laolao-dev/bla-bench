# What the artifact computes

`validateEnterpriseLicense` checks for a case-sensitive `ENT-` prefix. Without it, it returns `{valid: false, tier: "none"}` and omits `checksum`. Otherwise it compares the computed checksum to the supplied value coerced to an unsigned 32-bit integer. It returns the computed checksum and tier `enterprise-unlimited` on a match or `invalid` on a mismatch.

The checksum starts at `2166136261`. For each UTF-16 code unit in `license_key + ":" + customer + ":enterprise-v4"`, it XORs the code unit into the accumulator and multiplies by `16777619` modulo `2**32`. This is an FNV-1a-style checksum over UTF-16 code units, not a cryptographic signature.

`original/license-validator.js:974` maps the exports to the checksum body at line 811 and the validator at line 878. The decoder key uses the XOR of two latch words; the state update at lines 510–511 XORs the same value into both, preserving their XOR. An in-memory Node probe observed the same decoded suffix, hash constants, and tier labels across all 1,024 string-length residues used by the obfuscated seed. REA source recovery reported a missing Wakaru backend, and REA application analysis timed out, so the reconstruction rests on the shipped source and local probes.
