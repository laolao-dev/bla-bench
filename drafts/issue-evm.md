# Showcase Fixture Bug: `Vault.evm` (#12 in `src/engine/benchmark.ts`) `JUMPI` Offsets Land Off `JUMPDEST`

Hi — while building ground-truth equivalence runners for BLA's official showcase fixtures (`qybaihe/bla` v3.6.0, commit `8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`), we ran into a small bytecode jump-offset bug in showcase target #12 (`Vault.evm` in `src/engine/benchmark.ts`).

## Bytecode in `src/engine/benchmark.ts`

```text
60806040523615601b5760003560e01c806367e408a7146020575b005b602a60005260206000f3
```

Disassembly with exact byte offsets (`39` bytes total, `0x00..0x26`):

| PC (dec / hex) | Bytes | Instruction |
|---|---|---|
| `0 / 0x00` | `60 80 60 40 52` | `PUSH1 0x80; PUSH1 0x40; MSTORE` |
| `5 / 0x05` | `36 15` | `CALLDATASIZE; ISZERO` |
| `7 / 0x07` | `60 1b 57` | `PUSH1 0x1b; JUMPI` *(targets PC `27` / `0x1b`)* |
| `10 / 0x0a` | `60 00 35 60 e0 1c` | `PUSH1 0x00; CALLDATALOAD; PUSH1 0xe0; SHR` |
| `16 / 0x10` | `80 63 67e408a7 14` | `DUP1; PUSH4 0x67e408a7; EQ` |
| `23 / 0x17` | `60 20 57` | `PUSH1 0x20; JUMPI` *(targets PC `32` / `0x20`)* |
| `26 / 0x1a` | `5b` | **`JUMPDEST`** *(empty-calldata / fallback stop block)* |
| `27 / 0x1b` | `00` | `STOP` |
| `28 / 0x1c` | `5b` | **`JUMPDEST`** *(`return 42` block)* |
| `29 / 0x1d` | `60 2a 60 00 52` | `PUSH1 0x2a; PUSH1 0x00; MSTORE` *(bytes `31..32` = `60 00`)* |
| `34 / 0x22` | `60 20 60 00 f3` | `PUSH1 0x20; PUSH1 0x00; RETURN` |

## Issue

1. `PUSH1 0x1b; JUMPI` at bytes `7..9` jumps to PC `27` (`0x00 STOP`), whereas the `JUMPDEST` (`0x5b`) is at PC `26` (`0x1a`).
2. `PUSH1 0x20; JUMPI` at bytes `23..25` jumps to PC `32` (`0x00`, the immediate operand inside `PUSH1 0x00` at bytes `31..32`), whereas the `JUMPDEST` for the `return 42` block is at PC `28` (`0x1c`).

Under a Yellow-Paper-compliant EVM (requiring every `JUMP` / taken `JUMPI` target to be `0x5b JUMPDEST` outside `PUSH*` immediates), both empty calldata (`""`) and selector `0x67e408a7` halt with `BadJumpDestination`.

## Suggested Fix

Replacing `601b` → `601a` and `6020` → `601c` aligns both branches with their `JUMPDEST` instructions:

```text
60806040523615601a5760003560e01c806367e408a714601c575b005b602a60005260206000f3
```
