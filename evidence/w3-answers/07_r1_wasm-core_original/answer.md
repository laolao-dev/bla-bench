# `computeDigest`

The module's only export, `computeDigest`, takes two `i32` values and returns
`(left XOR right) + 42` modulo 2³². Despite its name, it is not a cryptographic
digest. The Python equivalent returns the signed interpretation of the result.

REA's `open_binary` reported an unsupported format, and its JEB provider was
unavailable. Direct inspection of `original/crypto-core.wasm` showed that the
export points to function 0. At file offset `0x2d`, its instructions are
`local.get 0; local.get 1; i32.xor; i32.const 42; i32.add; end`.
