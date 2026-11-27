# What the artifact computes

`computeLicenseChecksum` hashes `serialKey + ":" + productCode + ":enterprise-v4"` and returns an unsigned 32-bit integer. It uses the FNV-1a seed `0x811c9dc5` and multiplier `0x01000193`, but processes JavaScript UTF-16 code units rather than bytes. The exported `validateEnterpriseLicense` wrapper requires the `ENT-` prefix and compares the result with the expected checksum converted to an unsigned 32-bit integer.

REA’s static JavaScript analysis parsed the one artifact without errors (evidence `ev_95ffbdf8739c99789c65312152c77428982651339db0d9831613b926c68a5b00`). In `original/license-validator.js:2`, `charCodeAt` identifies the XOR input, and `Math.imul` followed by `>>> 0` shows the 32-bit wraparound. The wrapper at `original/license-validator.js:12` shows the prefix check, comparison, and returned tiers. The Python port covers string inputs and integer expected checksums.
