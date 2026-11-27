# Empirical Container Benchmark of BLA v3.6.0 Under Codex CLI + REA MCP (5 Official Targets, n=3)

Hi — sharing a reproducible, strictly isolated container benchmark measuring metered token usage, wall-clock time, and 12-case functional reconstruction accuracy under a specific experimental setup (**Codex CLI + REA MCP, single prompt per run, 5 official targets, `n=3` each**), plus a small jump-offset bug report on the `Vault.evm` showcase fixture.

## 1. Experimental Setup & Isolation

- **BLA**: `qybaihe/bla` v3.6.0 pinned at commit `8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`
- **Hardening command**: `node /opt/bla/dist/cli.js defend <input> -o <output> --intensity bankrupt --seed bla-benchmark-showcase-v1 --fail-under 0 --json`
- **Agent & Model**: `@openai/codex@0.171.0` (`model = "gpt-6.2-sol"`, `model_reasoning_effort = "low"`, `wire_api = "responses"`)
- **MCP Server**: `rea-agents@6.4.0` (`mcp_servers.rea.default_tools_approval_mode = "approve"`)
- **Runtime Container Isolation**: Multi-stage Docker build where the clean `runtime` image (`bla-bench:local`, rootless `uid=10001`, `--cap-drop ALL`, `--network bla-internal` with `Internal=true` + TCP relay to the model endpoint) contains **no** `/opt/bla`, **no** test/oracle scripts, **no** unhardened fixtures, and **no** mounted historical run logs (verified via full container readable-file audit in `evidence/isolation_check.txt`; JSONL logs are captured on the host from container stdout). Correctness checks run post-hoc in a separate `--network none` verifier container.
- **Empty-load baseline**: `11,092` input tokens across 3/3 container baseline runs (`cached = 3,968`, `output = 8`, 0 tool calls).

## 2. Scope & Difference From BLA's Modeled Estimates

**Under this experimental setup (Codex CLI + REA, single prompt, 5 samples, `n=3` each):**

- **What BLA's internal estimator (`bla benchmark` / `token-estimator.ts`) models**: the theoretical token cost if an agent **relies exclusively on REA's static analysis pipeline** (hitting default budgets or paging through decoy obligation graphs).
- **What our benchmark measures**: a general-purpose coding agent (`codex exec`) equipped with REA MCP inside a standard Linux runtime (Node `v24.22.2` + Python `3.12.16` + shell), where **the agent is permitted to bypass REA with local scripts** once REA's default static analyzers reject or truncate the hardened artifact.

> **Note on `sqlite-db` (`68/100` — below BLA's default `70/100` defense-score gate):** In default stock SQLite mode (without `--sqlite-eval-trap`, preserving standard SQLite client and `PRAGMA integrity_check` compatibility), `applyDefenseScoreHonesty` caps `sqlite-db` at `68/100` (`< 70` default `minDefenseScore` in `bla defend`), requiring `--fail-under 0` to emit. We flag `sqlite-db` explicitly as **below BLA's default defense-score gate** and report results separately for **gate-passing targets (4/5, score ≥ 70)** and **all targets (5/5)**.

## 3. Clean-Container Results (`n=3` Medians, Baseline `11,092` Deducted)

$$\text{Multiplier} = \frac{\text{median}(\text{hardened}_{\text{in}}) - 11{,}092}{\text{median}(\text{original}_{\text{in}}) - 11{,}092}$$

| Target | Format | BLA Score & Gate Status | `original` Median In | `hardened` Median In (Clean R2) | Median Time (`orig` → `hard`) | **Measured Net Multiplier (Agent Allowed to Bypass REA)** | BLA Modeled Multiplier (REA-Only Estimate) | `hardened` Interception Rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `dx-ball` | `.js` | `92/100` (pass) | 174,454 | 383,837 | 59.6s → 404.7s | **2.28×** | 4,817.7× | **0/3 (0%)** |
| `notion-electron` | `.asar` | `92/100` (pass) | 177,814 | 605,141 | 78.8s → 463.9s | **3.56×** | 2,532.3× | **0/3 (0%)** |
| `license-guard` | `.js` | `92/100` (pass) | 177,953 | 608,792 | 75.9s → 434.6s | **3.58×** | 4,817.7× | **0/3 (0%)** |
| `wasm-core` | `.wasm` | `93/100` (pass) | 198,641 | 359,023 | 63.4s → 101.5s | **1.86×** | 381.5× | **0/3 (0%)** |
| `sqlite-db`* | `.sqlite` | `68/100` (*below default 70 gate*, `--fail-under 0`) | 171,631 | 200,255 | 62.8s → 79.5s | **1.18×** | 152.5× | **0/3 (0%)** |

### Two-Group Summary

- **Gate-Passing Group (4 targets, defense score 92–93/100 ≥ 70)**:
  - Measured net input token multiplier: **`1.86×–3.58×`** (median **`2.92×`**), functional interception rate **`0/12 (0.0%)`** (`12/12` test cases matched on every run).
- **All-Samples Group (5 targets, including `sqlite-db` at `68/100`)**:
  - Measured net input token multiplier: **`1.18×–3.58×`** (median **`2.28×`**), functional interception rate **`0/15 (0.0%)`**.

## 4. JSONL Evidence of Direct Artifact Parsing After REA Budget Rejection

Across the hardened runs, REA's static analyzers tripped BLA's resource limits or format refusals as designed, after which Codex immediately switched to local script inspection of `./original/*`:

- **`dx-ball`**: `runs/20261127T035024721349+0000_dx-ball_hardened.jsonl#L9` (`rea.analyze_javascript_application` failed) → `#L11` (`rg`/`head`/`tail` slicing `original/*.js`); also `runs/20261127T041554828409+0000_dx-ball_hardened.jsonl#L7` → `#L9` and `runs/20261127T044054517732+0000_dx-ball_hardened.jsonl#L7` → `#L9`.
- **`notion-electron`**: `runs/20261127T035709869570+0000_notion-electron_hardened.jsonl#L7` (`rea.analyze_javascript_application` rejected 24.7 MB ASAR header) → `#L9` (`python` `struct.unpack('<4I', f.read(16))` reading the ASAR Pickle header directly); also `runs/20261127T042252436598+0000_notion-electron_hardened.jsonl#L7` → `#L9` and `runs/20261127T044739798280+0000_notion-electron_hardened.jsonl#L7` → `#L9`.
- **`license-guard`**: `runs/20261127T040459701592+0000_license-guard_hardened.jsonl#L7` (`rea.analyze_javascript_application` failed) → `#L9` (`head`/`tail` slicing `original/license-validator.js`); also `runs/20261127T043043188735+0000_license-guard_hardened.jsonl#L7` → `#L9` and `runs/20261127T045511098499+0000_license-guard_hardened.jsonl#L7` → `#L9`.
- **`wasm-core`**: `runs/20261127T041225208013+0000_wasm-core_hardened.jsonl#L7` (`rea.inspect_binary_layout` failed) → `#L13` (`xxd`/`strings`/`node` `WebAssembly.Module` & LEB128 section parser on `original/crypto-core.wasm`); also `runs/20261127T043752250802+0000_wasm-core_hardened.jsonl#L7` → `#L11` and `runs/20261127T050224238746+0000_wasm-core_hardened.jsonl#L7` → `#L9`.
- **`sqlite-db`**: `runs/20261127T041448976791+0000_sqlite-db_hardened.jsonl#L7` (`rea.open_binary` failed) → `#L9` (`python` `sqlite3.connect` inspecting `sqlite_schema`); `runs/20261127T043934344763+0000_sqlite-db_hardened.jsonl#L7` (`python3` `sqlite3` invoked via `rea.capture_process_scenario`); `runs/20261127T050404617803+0000_sqlite-db_hardened.jsonl#L7` → `#L9`.

This suggests mechanical single-artifact shields (`bla defend` without Stage-2 host-agent source weaving / cross-artifact entanglement) stop default REA passes and add `~5.7×–6.8×` wall-clock delay on JS/ASAR, but do not prevent a shell-capable coding agent from recovering small standalone functions.

## 5. Additional Fixture Bug: `Vault.evm` (#12 in `src/engine/benchmark.ts`) Jump Offsets

While writing a Yellow-Paper EVM interpreter for target #12 (`Vault.evm`: `60806040523615601b5760003560e01c806367e408a7146020575b005b602a60005260206000f3`), we found two jump-offset errors:

- `PUSH1 0x1b; JUMPI` (`bytes 7..9`) targets PC `27` (`0x00 STOP`), whereas `JUMPDEST` (`0x5b`) is at PC `26` (`0x1a`).
- `PUSH1 0x20; JUMPI` (`bytes 23..25`) targets PC `32` (inside `PUSH1 0x00` at `bytes 31..32`), whereas `JUMPDEST` for the `return 42` block is at PC `28` (`0x1c`).

Both empty calldata and selector `0x67e408a7` therefore revert with `BadJumpDestination` in a spec-compliant EVM. Changing `601b` → `601a` and `6020` → `601c` fixes both branches.
