# Enterprise license validator

REA identified `original/license-validator.js` as JavaScript and statically parsed it with no parse failures. Line 22 exports both the checksum function and the validator.

- Lines 2–10 compute a 32-bit FNV-1a-style checksum over `serialKey:productCode:enterprise-v4`. Starting at `0x811c9dc5`, the loop XORs each UTF-16 code unit into the state and multiplies by `0x01000193` modulo 2³². It does not hash UTF-8 bytes.
- Lines 12–19 reject serials without the `ENT-` prefix with tier `none` and no checksum. Otherwise the validator returns the computed checksum and selects `enterprise-unlimited` on a match with the unsigned 32-bit expected value, or `invalid` on a mismatch.

The Python port covers string inputs, a missing serial (`None`), and integer checksums, not arbitrary JavaScript coercions.
