# What `computeDigest` computes

The sole export takes two `i32` values and returns their bitwise XOR plus 42, wrapping modulo 2³². Despite its name, it is not a cryptographic digest. Python returns the result as an unsigned 32-bit integer; JavaScript exposes the same Wasm bits as a signed integer.

REA's `open_binary` rejected the WebAssembly format, so I decoded the bytes directly. The type and export sections identify `computeDigest` as function 0 with signature `(i32, i32) -> i32`. Starting at file offset `0x2d`, its instructions are `20 00` (`local.get 0`), `20 01` (`local.get 1`), `73` (`i32.xor`), `41 2a` (`i32.const 42`), `6a` (`i32.add`), and `0b` (`end`).
