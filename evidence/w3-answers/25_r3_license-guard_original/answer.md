# License validator

REA's `open_binary` identified `original/license-validator.js` as JavaScript. Line 22 exports a validator and its checksum helper; there is no separate `main` function.

- Lines 12–19 reject missing or non-`ENT-` serials with tier `none`. For an `ENT-` serial, the validator returns the computed checksum and assigns tier `enterprise-unlimited` if it matches the expected unsigned 32-bit checksum, or `invalid` otherwise.
- Lines 2–9 start the checksum at `0x811c9dc5`, then XOR each UTF-16 code unit of `serial:product:enterprise-v4` and multiply by `0x01000193` modulo 2³². This is FNV-1a-style, but it processes UTF-16 code units rather than bytes.

The Python port preserves UTF-16 code units, including surrogate pairs and lone surrogates. It accepts string keys and product codes and integer expected checksums, without emulating JavaScript's general-purpose type coercion.
