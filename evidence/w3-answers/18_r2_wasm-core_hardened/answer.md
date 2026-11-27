# What the function computes

The sole function in `original/crypto-core.wasm` takes two `i32` arguments and returns `(left XOR right) + 42` modulo 2³². All 251 exports point to function index 0, including `ops_4f61_matrix_segment_dispatch_gtc`. The Python function returns the signed interpretation of the resulting 32-bit word.

REA's `open_binary` rejected the WebAssembly format, so I decoded the module's standard sections and instruction bytes directly. The result-producing instructions are `local.get 0; local.get 1; i32.xor; i32.const 42; i32.add`. The two preceding branches test whether `x | (x - 1)` is less than `x ^ (x - 1)` as unsigned words. That is always false because OR contains every XOR bit. The two trailing branches are also unreachable: consecutive integers have an even product, and an odd square is always 1 modulo 8. The sum stays on the stack as the return value.
