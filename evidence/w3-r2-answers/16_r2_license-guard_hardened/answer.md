# What the artifact computes

The main export, `validateEnterpriseLicense`, checks that the key starts with `ENT-`, then compares a locally computed checksum with the supplied checksum interpreted as an unsigned 32-bit integer. A missing prefix returns `{valid: false, tier: "none"}` without a checksum. With the prefix, the result includes the computed checksum and reports `enterprise-unlimited` on a match or `invalid` otherwise.

`computeLicenseChecksum` applies an FNV-1a-style recurrence to `key + ":" + organization + ":enterprise-v4"`: start at `2166136261`, XOR each JavaScript UTF-16 code unit, and multiply by `16777619` modulo `2^32`. This is a checksum, not a cryptographic signature.

## Evidence

- `original/license-validator.js:974` maps the exports to `projectLocalCursorR50` (line 811, checksum loop at line 827) and `deriveCompositeStreamHak` (line 878, checksum comparison at line 908).
- The initialized seed is `3764720783`. Input-dependent changes start at bit 8, and the cursor update at line 510 XORs both latch words with the same value, preserving their XOR. Evaluating the opaque branches and string decoders yields the fixed suffix, prefix, and tier labels above.
- REA's JavaScript application analysis timed out. I checked the reconstruction against isolated JavaScript function bodies and initialization logic without running the whole bundle. Python matched 3,072 checksum cases and 6,144 validation cases, covering all 1,024 string-length residues and including non-BMP text. The Python API models string keys and organizations and integer checksum claims, not arbitrary JavaScript coercions.
