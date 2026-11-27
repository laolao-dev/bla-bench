# What `computeDigest` computes

The module's sole export, `computeDigest`, takes two `i32` values and returns
`(left XOR right) + 42` modulo `2**32`. The Python function returns the same
32-bit pattern interpreted as a signed integer.

REA's `open_binary` reported that the format was unsupported, so I decoded the
module directly. The export section maps `computeDigest` to function index 0,
whose type is `(i32, i32) -> i32`. Its instructions start at file offset `0x2d`:
`20 00` and `20 01` load the arguments, `73` XORs them, `41 2a` pushes 42,
`6a` adds with 32-bit wraparound, and `0b` ends the function.
