# Empirical Container Benchmark of BLA v3.6.0 Under Codex CLI + REA MCP (5 Official Targets, n=3)

Hi — thanks for open-sourcing BLA! Sharing a reproducible, strictly isolated container benchmark measuring metered token usage, wall-clock time, and 12-case functional reconstruction accuracy under a specific experimental setup (**Codex CLI + REA MCP, single prompt per run, 5 official targets, `n=3` each**).

First, what worked as intended: **REA's default static analysis was stopped across all `15/15` hardened runs** (`14/15` explicit static-analyzer rejections, plus `1/15` `sqlite-db` run where static REA tools were skipped in favor of `rea.capture_process_scenario`), and **hardening increased median wall-clock time on the JS/ASAR targets by `~5.7×–6.8×`** (`59.6s → 404.7s` on `dx-ball`, `75.9s → 434.6s` on `license-guard`, and `78.8s → 463.9s` on `notion-electron`).

## 1. Experimental Setup & Isolation

- **BLA**: `qybaihe/bla` v3.6.0 pinned at commit `8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`
- **Hardening command**: `node /opt/bla/dist/cli.js defend <input> -o <output> --intensity bankrupt --seed bla-benchmark-showcase-v1 --fail-under 0 --json`
  - *Note on `--fail-under 0`*: This flag **only affected `sqlite-db`** (`68/100` in stock SQLite mode, below BLA's default `70/100` defense-score gate); the other 4 targets scored `92–93/100` and already passed the default gate without it.
- **Agent & Model**: `@openai/codex@0.171.0` (`requested model: gpt-6.2-sol (served via a local relay; served model not independently verified)`, `model_reasoning_effort = "low"`, `wire_api = "responses"`)
- **MCP Server**: `rea-agents@6.4.0` (`mcp_servers.rea.default_tools_approval_mode = "approve"`)
- **Runtime Container Isolation**: Multi-stage Docker build ([`Dockerfile`](https://github.com/laolao-dev/bla-bench/blob/main/Dockerfile)) where the clean `runtime` image (`bla-bench:local`, rootless `uid=10001`, `--cap-drop ALL`, `--network bla-internal` with `Internal=true` + TCP relay to the model endpoint) contains **no** `/opt/bla`, **no** test/oracle scripts, **no** unhardened fixtures, and **no** mounted historical run logs (verified via full container readable-file audit in [`evidence/isolation_check.txt`](https://github.com/laolao-dev/bla-bench/blob/main/evidence/isolation_check.txt); JSONL logs are captured on the host from container stdout). Correctness checks run post-hoc in a separate `--network none` verifier container.
- **Empty-load baseline**: `11,092` input tokens across `3/3` container baseline runs (`cached = 3,968`, `output = 8`, `0` tool calls).

## 2. Scope & Difference From BLA's Modeled Estimates

**Under this experimental setup (Codex CLI + REA, single prompt, 5 samples, `n=3` each):**

- **BLA's internal estimator (`bla benchmark` / `token-estimator.ts`)**: Our understanding is that it models the theoretical token cost when an agent **relies exclusively on REA's static analysis pipeline** (hitting default budgets or paging through decoy obligation graphs) — please correct us if this is wrong.
- **What our benchmark measures**: A general-purpose coding agent (`codex exec`) equipped with REA MCP inside a standard Linux runtime (Node `v24.22.2` + Python `3.12.16` + shell), where **the agent is permitted to fall back to local scripts** once REA's default static analyzers reject or truncate the hardened artifact.

> **Note on `sqlite-db` (`68/100` — below BLA's default `70/100` defense-score gate):** In default stock SQLite mode (without `--sqlite-eval-trap`, preserving standard SQLite client and `PRAGMA integrity_check` compatibility), `applyDefenseScoreHonesty` caps `sqlite-db` at `68/100` (`< 70` default `minDefenseScore` in `bla defend`). We flag `sqlite-db` explicitly and report results separately for **gate-passing targets (4/5, score ≥ 70)** and **all targets (5/5)**.

## 3. Clean-Container Results (`n=3` Medians, Baseline `11,092` Deducted)

Full per-run CSV: [`evidence/w3_r2_runs.csv`](https://github.com/laolao-dev/bla-bench/blob/main/evidence/w3_r2_runs.csv)

$$\text{Multiplier} = \frac{\text{median}(\text{hardened}_{\text{in}}) - 11{,}092}{\text{median}(\text{original}_{\text{in}}) - 11{,}092}$$

| Target | Format | BLA Score & Gate Status | `original` Median In | `hardened` Median In (Clean R2) | Median Time (`orig` → `hard`) | **Measured Net Multiplier** | BLA Modeled Multiplier (REA-Only Estimate) | `hardened` Interception Rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `dx-ball` | `.js` | `92/100` (pass) | 174,454 | 383,837 | 59.6s → 404.7s | **2.28×** | 4,817.7× | **0/3 (0%)** |
| `notion-electron` | `.asar` | `92/100` (pass) | 177,814 | 605,141 | 78.8s → 463.9s | **3.56×** | 2,532.3× | **0/3 (0%)** |
| `license-guard` | `.js` | `92/100` (pass) | 177,953 | 608,792 | 75.9s → 434.6s | **3.58×** | 4,817.7× | **0/3 (0%)** |
| `wasm-core` | `.wasm` | `93/100` (pass) | 198,641 | 359,023 | 63.4s → 101.5s | **1.86×** | 381.5× | **0/3 (0%)** |
| `sqlite-db`* | `.sqlite` | `68/100` (*below default 70 gate*, `--fail-under 0`) | 171,631 | 200,255 | 62.8s → 79.5s | **1.18×** | 152.5× | **0/3 (0%)** |

### Two-Group Summary

- **Gate-Passing Group (4 targets, defense score `92–93/100` ≥ 70)**:
  - Measured net input token multiplier: **`1.86×–3.58×`** (median **`2.92×`**), functional interception rate **`0/12 (0.0%)`** (`12/12` test cases matched on every run).
- **All-Samples Group (5 targets, including `sqlite-db` at `68/100`)**:
  - Measured net input token multiplier: **`1.18×–3.58×`** (median **`2.28×`**), functional interception rate **`0/15 (0.0%)`**.

## 4. JSONL Evidence of Direct Artifact Parsing (`14/15` Runs) vs. REA Dynamic Execution (`1/15` Run)

In `14/15` hardened runs, REA's static analyzers tripped BLA's resource limits or format refusals as designed, after which Codex switched to local shell/Python/Node scripts on `./original/*` (the remaining `1/15` run — `sqlite-db` run 2 — was executed through REA's own `capture_process_scenario` tool and is noted separately below):

- **`dx-ball`**:
  - Run 1: [`20261127T035024721349+0000_dx-ball_hardened.jsonl#L9`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T035024721349+0000_dx-ball_hardened.jsonl#L9) (`rea.analyze_javascript_application` failed) → [`#L11`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T035024721349+0000_dx-ball_hardened.jsonl#L11) (`rg`/`head`/`tail` slicing `original/*.js`)
  - Run 2: [`20261127T041554828409+0000_dx-ball_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T041554828409+0000_dx-ball_hardened.jsonl#L7) → [`#L9`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T041554828409+0000_dx-ball_hardened.jsonl#L9)
  - Run 3: [`20261127T044054517732+0000_dx-ball_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T044054517732+0000_dx-ball_hardened.jsonl#L7) → [`#L9`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T044054517732+0000_dx-ball_hardened.jsonl#L9)
- **`notion-electron`**:
  - Run 1: [`20261127T035709869570+0000_notion-electron_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T035709869570+0000_notion-electron_hardened.jsonl#L7) (`rea.analyze_javascript_application` rejected 24.7 MB ASAR header) → [`#L9`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T035709869570+0000_notion-electron_hardened.jsonl#L9) (`python` `struct.unpack('<4I', f.read(16))` reading the ASAR Pickle header directly)
  - Run 2: [`20261127T042252436598+0000_notion-electron_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T042252436598+0000_notion-electron_hardened.jsonl#L7) → [`#L9`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T042252436598+0000_notion-electron_hardened.jsonl#L9)
  - Run 3: [`20261127T044739798280+0000_notion-electron_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T044739798280+0000_notion-electron_hardened.jsonl#L7) → [`#L9`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T044739798280+0000_notion-electron_hardened.jsonl#L9)
- **`license-guard`**:
  - Run 1: [`20261127T040459701592+0000_license-guard_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T040459701592+0000_license-guard_hardened.jsonl#L7) (`rea.analyze_javascript_application` failed) → [`#L9`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T040459701592+0000_license-guard_hardened.jsonl#L9) (`head`/`tail` slicing `original/license-validator.js`)
  - Run 2: [`20261127T043037063791+0000_license-guard_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T043037063791+0000_license-guard_hardened.jsonl#L7) → [`#L9`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T043037063791+0000_license-guard_hardened.jsonl#L9)
  - Run 3: [`20261127T045511098499+0000_license-guard_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T045511098499+0000_license-guard_hardened.jsonl#L7) → [`#L9`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T045511098499+0000_license-guard_hardened.jsonl#L9)
- **`wasm-core`**:
  - Run 1: [`20261127T041225208013+0000_wasm-core_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T041225208013+0000_wasm-core_hardened.jsonl#L7) (`rea.inspect_binary_layout` failed) → [`#L13`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T041225208013+0000_wasm-core_hardened.jsonl#L13) (`xxd`/`strings`/Python section parser on `original/crypto-core.wasm`)
  - Run 2: [`20261127T043752250802+0000_wasm-core_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T043752250802+0000_wasm-core_hardened.jsonl#L7) (`rea.inspect_binary_layout` failed) → [`#L11`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T043752250802+0000_wasm-core_hardened.jsonl#L11) (`xxd`/`strings`/Node section parser)
  - Run 3: [`20261127T050224238746+0000_wasm-core_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T050224238746+0000_wasm-core_hardened.jsonl#L7) (`rea.open_binary` failed) → [`#L9`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T050224238746+0000_wasm-core_hardened.jsonl#L9) (`xxd`/`strings`/Node section parser)
- **`sqlite-db`**:
  - Run 1: [`20261127T041448976791+0000_sqlite-db_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T041448976791+0000_sqlite-db_hardened.jsonl#L7) (`rea.open_binary` failed) → [`#L9`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T041448976791+0000_sqlite-db_hardened.jsonl#L9) (`python` `sqlite3.connect` inspecting `sqlite_schema`)
  - Run 2 (*not counted as bypassing REA*): [`20261127T043934344763+0000_sqlite-db_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T043934344763+0000_sqlite-db_hardened.jsonl#L7) and [`#L9`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T043934344763+0000_sqlite-db_hardened.jsonl#L9) — executed **by REA itself** via `rea.capture_process_scenario` spawning `python3` `sqlite3` against `original/entitlements.sqlite`
  - Run 3: [`20261127T050404617803+0000_sqlite-db_hardened.jsonl#L7`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T050404617803+0000_sqlite-db_hardened.jsonl#L7) (`rea.open_binary` failed) → [`#L9`](https://github.com/laolao-dev/bla-bench/blob/main/runs/20261127T050404617803+0000_sqlite-db_hardened.jsonl#L9) (`python` `sqlite3.connect` inspecting `sqlite_schema`)

In our runs, mechanical single-artifact shields (`bla defend` without Stage-2 host-agent source weaving / cross-artifact entanglement) stopped default REA static passes and added `~5.7×–6.8×` wall-clock delay on JS/ASAR, while a shell-capable coding agent was still able to recover these small standalone functions.

## 5. Limitations

- **Single agent harness**: We only tested one coding agent (`@openai/codex@0.171.0`). Other agents or tool policies (e.g., restricting arbitrary shell execution) may behave differently.
- **Reasoning effort (`low`)**: All runs used `model_reasoning_effort = "low"`. Because even the `low` tier reconstructed `15/15` hardened runs (`12/12` test cases each), this makes the `0%` interception observation stronger; however, net token multipliers could differ at higher reasoning-effort settings.
- **Sample size & prompting**: Each `(target, variant)` pair was run `n=3` times using a single task prompt per target.
- **Stage-1 CLI scope only**: We did not test Stage-2 host-agent source weaving or cross-artifact entanglement.
- **Round-1 isolation disclosure & Round-2 clean rerun**: Our first 30-run pass ([`evidence/w3_runs.csv`](https://github.com/laolao-dev/bla-bench/blob/main/evidence/w3_runs.csv)) had incomplete static container isolation (`/opt/bla`, test scripts, and `/bench/runs` were still present in the single-stage image/mounts), although a line-by-line JSONL audit confirmed **`0/15` out-of-directory reads**. After stripping those directories from the runtime image and verifying isolation ([`evidence/isolation_check.txt`](https://github.com/laolao-dev/bla-bench/blob/main/evidence/isolation_check.txt)), we reran all 15 `hardened` runs; conclusions matched closely (gate-passing median multiplier **`2.67×`** in Round 1 vs. **`2.92×`** in Round 2; `0%` interception in both).

---

Full reproduction scripts, Dockerfiles, sanitized JSONL logs, and 12-case equivalence checks: https://github.com/laolao-dev/bla-bench

If we misconfigured anything in BLA or REA, please let us know — we would be happy to rerun the benchmark under settings you recommend!
