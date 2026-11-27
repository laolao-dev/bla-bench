# bla-bench

Containerized, reproducible benchmark measuring [BLA](https://github.com/qybaihe/bla) v3.6.0 (`bankrupt` hardening) against Codex CLI + REA MCP across 5 official targets (`n=3` per condition).

**Status:** Active

![BLA v3.6.0 Container Benchmark Comparison](evidence/w3_comparison.png)

## Why

BLA's built-in `benchmark` estimator projects `152.5×–4,817.7×` input-token multipliers by modeling an agent that relies exclusively on [REA](https://www.npmjs.com/package/rea-agents)'s static analysis pipeline. General-purpose coding agents, however, run inside a standard Linux shell with Python and Node available alongside MCP tools. `bla-bench` measures actual metered token usage, wall-clock delay, REA tool behavior, and 12-case functional equivalence when Codex CLI (`@openai/codex@0.171.0`) + REA (`rea-agents@6.4.0`) analyzes unhardened (`original`) vs. `bankrupt`-hardened (`hardened`) BLA targets inside network- and filesystem-isolated Docker containers.

## Findings

**Under this experimental setup (Codex CLI + REA MCP, single prompt per target, 5 official targets, `n=3` each):**

- **What BLA stopped:** REA's default static analysis never succeeded on a hardened target across all `15/15` clean-container runs (`14/15` explicit static-analyzer rejections; `1/15` `sqlite-db` run skipped static REA tools and used `rea.capture_process_scenario`), increasing median wall-clock time on JS/ASAR targets by **`~5.7×–6.8×`**.
- **What happened next:** Once REA rejected or truncated an artifact, the agent pivoted to targeted local Python/Node/shell inspection of `./original/*` and reconstructed equivalent Python logic passing `12/12` ground-truth checks on every run:
  - **Gate-passing targets (4/5, BLA defense score `92–93/100` ≥ default `70` gate):** net input-token multiplier **`1.86×–3.58×`** (median **`2.92×`**), functional interception rate **`0/12 (0.0%)`**.
  - **All targets (5/5, including `sqlite-db` at `68/100`, below BLA's default `70` gate):** net input-token multiplier **`1.18×–3.58×`** (median **`2.28×`**), functional interception rate **`0/15 (0.0%)`**.
- **Scope difference vs. BLA's estimate:** BLA's `152.5×–4,817.7×` figures estimate REA-only static-pipeline cost; our `1.18×–3.58×` figures measure an agent permitted to bypass REA with local scripts after REA rejects the artifact. Upstream reports: [qybaihe/bla#319](https://github.com/qybaihe/bla/issues/319) (benchmark data) and [qybaihe/bla#320](https://github.com/qybaihe/bla/issues/320) (`Vault.evm` jump-offset bug).

### Clean-Container Results (`n=3` Medians, Empty-Load Baseline `11,092` Deducted)

Full per-run data: [evidence/w3_r2_runs.csv](evidence/w3_r2_runs.csv) · Aggregated stats: [evidence/w3_summary.json](evidence/w3_summary.json)

$$\text{Multiplier} = \frac{\text{median}(\text{hardened}_{\text{in}}) - 11{,}092}{\text{median}(\text{original}_{\text{in}}) - 11{,}092}$$

| Target | Format | Original → Hardened Size | BLA Score & Gate Status | `original` Median In | `hardened` Median In (R2) | Median Time (`orig` → `hard`) | **Measured Net Multiplier** | BLA Modeled Estimate (REA-Only) | `hardened` Interception |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| `dx-ball` | `.js` | 403 B → 170,886 B | `92/100` (pass) | 174,454 | 383,837 | 59.6s → 404.7s | **2.28×** | 4,817.7× | 0/3 (0%) |
| `notion-electron` | `.asar` | 1,769 B → 24,671,339 B | `92/100` (pass) | 177,814 | 605,141 | 78.8s → 463.9s | **3.56×** | 2,532.3× | 0/3 (0%) |
| `license-guard` | `.js` | 782 B → 183,188 B | `92/100` (pass) | 177,953 | 608,792 | 75.9s → 434.6s | **3.58×** | 4,817.7× | 0/3 (0%) |
| `wasm-core` | `.wasm` | 54 B → 6,880,378 B | `93/100` (pass) | 198,641 | 359,023 | 63.4s → 101.5s | **1.86×** | 381.5× | 0/3 (0%) |
| `sqlite-db`* | `.sqlite` | 12,288 B → 49,152 B | `68/100` (**below default 70 gate**, `--fail-under 0`) | 171,631 | 200,255 | 62.8s → 79.5s | **1.18×** | 152.5× | 0/3 (0%) |

- `*` **`sqlite-db` gate note:** In stock SQLite mode (preserving standard SQLite client and `PRAGMA integrity_check` compatibility without `--sqlite-eval-trap`), BLA caps `sqlite-db` at `68/100` (`< 70` default `minDefenseScore`), requiring `--fail-under 0` to emit. The other 4 targets scored `92–93/100` and already passed the default gate without `--fail-under 0`.
- **JSONL evidence of direct artifact parsing (`14/15` runs) vs. REA dynamic execution (`1/15` run):**
  - `dx-ball`: `runs/20261127T035024721349+0000_dx-ball_hardened.jsonl#L9` (`rea.analyze_javascript_application` failed) → `#L11` (`rg`/`head`/`tail` slicing `original/*.js`); also `runs/20261127T041554828409+0000_dx-ball_hardened.jsonl#L7` → `#L9` and `runs/20261127T044054517732+0000_dx-ball_hardened.jsonl#L7` → `#L9`.
  - `notion-electron`: `runs/20261127T035709869570+0000_notion-electron_hardened.jsonl#L7` (`rea.analyze_javascript_application` rejected 24.7 MB ASAR header) → `#L9` (`python` `struct.unpack('<4I', f.read(16))` unpacking the ASAR header directly); also `runs/20261127T042252436598+0000_notion-electron_hardened.jsonl#L7` → `#L9` and `runs/20261127T044739798280+0000_notion-electron_hardened.jsonl#L7` → `#L9`.
  - `license-guard`: `runs/20261127T040459701592+0000_license-guard_hardened.jsonl#L7` (`rea.analyze_javascript_application` failed) → `#L9` (`head`/`tail` slicing `original/license-validator.js`); also `runs/20261127T043037063791+0000_license-guard_hardened.jsonl#L7` → `#L9` and `runs/20261127T045511098499+0000_license-guard_hardened.jsonl#L7` → `#L9`.
  - `wasm-core`: `runs/20261127T041225208013+0000_wasm-core_hardened.jsonl#L7` (`rea.inspect_binary_layout` failed) → `#L13` (`xxd`/`strings`/Python section parser on `original/crypto-core.wasm`); also `runs/20261127T043752250802+0000_wasm-core_hardened.jsonl#L7` → `#L11` and `runs/20261127T050224238746+0000_wasm-core_hardened.jsonl#L7` (`rea.open_binary` failed) → `#L9`.
  - `sqlite-db`: `runs/20261127T041448976791+0000_sqlite-db_hardened.jsonl#L7` (`rea.open_binary` failed) → `#L9` (`python` `sqlite3.connect` inspecting `sqlite_schema`), and run 3 `runs/20261127T050404617803+0000_sqlite-db_hardened.jsonl#L7` → `#L9`. Note: run 2 (`runs/20261127T043934344763+0000_sqlite-db_hardened.jsonl#L7`, `#L9`) was executed by REA itself via `rea.capture_process_scenario` invoking `python3 sqlite3`, and is not counted as bypassing REA.

### Round-1 vs. Round-2 Isolation Disclosure

During pre-release audit of Round 1 ([evidence/w3_runs.csv](evidence/w3_runs.csv)), we found that the single-stage container image still contained `/opt/bla`, `/bench/tests`, `/bench/scripts`, and `/bench/fixtures/dx-ball`, and mounted `/bench/runs`. A line-by-line audit of all 15 Round-1 hardened JSONL logs confirmed **`0/15` out-of-directory reads**. To eliminate any static boundary gap, Round 2 split [Dockerfile](Dockerfile) into `bla-bench:verifier` and a stripped `bla-bench:local` runtime image, removed host log mounts, verified `STATUS: CLEAN` in [evidence/isolation_check.txt](evidence/isolation_check.txt), and reran all 15 `hardened` runs (reusing the 15 `original` runs and the `11,092` baseline):

| Target / Group | R1 `hardened` Median In | R2 `hardened` Median In | R1 Multiplier | R2 Multiplier | Diff (Rel.) | R1 Interception | R2 Interception |
|---|---:|---:|---:|---:|---:|---:|---:|
| `dx-ball` | 370,423 | 383,837 | 2.20× | **2.28×** | +0.08× (+3.6%) | 0/3 (0%) | **0/3 (0%)** |
| `notion-electron` | 545,882 | 605,141 | 3.21× | **3.56×** | +0.35× (+10.9%) | 0/3 (0%) | **0/3 (0%)** |
| `license-guard` | 533,595 | 608,792 | 3.13× | **3.58×** | +0.45× (+14.4%) | 0/3 (0%) | **0/3 (0%)** |
| `wasm-core` | 300,269 | 359,023 | 1.54× | **1.86×** | +0.32× (+20.8%) | 0/3 (0%) | **0/3 (0%)** |
| `sqlite-db`* (`68/100`, below gate) | 208,006 | 200,255 | 1.23× | **1.18×** | -0.05× (-4.1%) | 0/3 (0%) | **0/3 (0%)** |
| **Gate-passing median (4 targets)** | — | — | 2.67× | **2.92×** | +0.25× (+9.4%) | 0/12 (0%) | **0/12 (0%)** |
| **All-targets median (5 targets)** | — | — | 2.20× | **2.28×** | +0.08× (+3.6%) | 0/15 (0%) | **0/15 (0%)** |

## Experimental Setup

- **Container & network isolation:**
  - Base digests pinned in [Dockerfile](Dockerfile): `python:3.12.16-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64` + `node:24.22.2-bookworm-slim@sha256:01d566e8d94d8c619591d78652babfccd3c6992a3dffa9ed5ab39e11cf6c70e9` (non-root user `bench` `uid=10001`, `--cap-drop ALL --security-opt no-new-privileges`).
  - Network: `--internal` Docker network `bla-internal` (verified `Internal=true` before launch) with a stateless TCP forwarder `bla-relay` to the host model endpoint (`:8317`); 12-case equivalence checks run in a separate `--network none` `bla-bench:verifier` container.
  - Filesystem: `bla-bench:local` contains no `/opt/bla`, tests, oracle scripts, unhardened fixtures, or historical `runs/` mounts ([evidence/isolation_check.txt](evidence/isolation_check.txt)).
- **Agent & MCP stack:**
  - Codex CLI: `@openai/codex@0.171.0` (`requested model: gpt-6.2-sol (served via a local relay; served model not independently verified)` — `codex exec --json` events do not emit upstream served-model metadata; `model_reasoning_effort = "low"`, `wire_api = "responses"`, `js_repl = false`, `memories = false` in [docker/codex-config.toml](docker/codex-config.toml)).
  - MCP server: `rea-agents@6.4.0` (`-c 'mcp_servers.rea.default_tools_approval_mode="approve"'`), 900s per-run timeout (0 timeouts across 45 target runs + 3 baseline runs).
- **BLA version & hardening command:**
  - `qybaihe/bla` (`bla-agents@3.6.0`), commit `8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`.
  - Command: `node /opt/bla/dist/cli.js defend <input> -o <output> --intensity bankrupt --seed bla-benchmark-showcase-v1 --fail-under 0 --json` ([evidence/hardening_manifest.json](evidence/hardening_manifest.json)).
- **Prompts (identical across `original` and `hardened`):**
  - Default prompt ([prompt.txt](prompt.txt), used for `dx-ball`, `license-guard`, `wasm-core`):
    ```text
    Use the REA tools to analyze the artifact in ./original. Determine what its main function computes, write an equivalent Python function to ./answer.py, and explain your evidence briefly in ./answer.md. Do not access files outside this directory.
    ```
  - Electron ASAR prompt ([prompts/notion-electron.txt](prompts/notion-electron.txt)):
    ```text
    Use the REA tools to analyze the artifact in ./original. Determine what its Electron main-process IPC module computes, write an equivalent Python function register_handlers(store, ipc_main, fetch_fn=None) to ./answer.py (where store provides .get(key) and .set(key, value), ipc_main provides .handle(channel, handler) for sync or async (event, *args) handlers, and optional fetch_fn(url) replaces global fetch), and explain your evidence briefly in ./answer.md. Do not access files outside this directory.
    ```
  - SQLite prompt ([prompts/sqlite-db.txt](prompts/sqlite-db.txt)):
    ```text
    Use the REA tools to analyze the artifact in ./original. Determine the genuine business entitlement records stored in this SQLite database, write an equivalent Python function query_entitlements(account_id: str | None = None) -> list[dict] to ./answer.py (returning all genuine business rows ordered by primary key when account_id is None, or the matching business row(s) as dicts mapping column name to value when account_id is a string), and explain your evidence briefly in ./answer.md. Do not access files outside this directory.
    ```
  - Empty-load baseline prompt ([prompt-baseline.txt](prompt-baseline.txt)):
    ```text
    Reply with exactly one short sentence confirming you are ready. Do not run any commands, do not call any tools, and do not read or write any files.
    ```

## Quickstart

Requires Windows + Docker Desktop (WSL2 engine) + [uv](https://docs.astral.sh/uv/). Live model runs additionally require `%USERPROFILE%\.codex\auth.json`, `cpa-gui-model-catalog.json`, and an OpenAI-compatible Responses endpoint on `127.0.0.1:8317`.

```powershell
# 1. Local unit tests and lint checks (no Docker or API key required)
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .

# 2. Build verifier + clean runtime images, run offline checks & container isolation audit
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-docker.ps1 -Stage check
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-docker.ps1 -Stage isolation-check

# 3. Generate deterministic hardened artifacts in the offline verifier container
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-docker.ps1 -Stage harden

# 4. Run the 15 clean-container hardened evaluations and regenerate plots/statistics
uv run python scripts\run_w3_r2.py
uv run python scripts\analyze_w3.py
```

Target selection criteria and excluded fixtures (including the `Vault.evm` jump-offset bug) are documented in [samples.md](samples.md); additional notes are in [NOTES.md](NOTES.md) and [evidence/DOCKER_REPORT.md](evidence/DOCKER_REPORT.md).

## Limitations

- **Single agent harness:** Only `@openai/codex@0.171.0` with shell access enabled inside the container was tested; agents restricted to MCP tools without arbitrary shell execution would face REA's refusals directly.
- **Reasoning effort (`low`):** Running at `model_reasoning_effort = "low"` strengthens the `0%` interception finding (even low-effort runs recovered all 5 targets), but net token multipliers may differ at higher reasoning-effort tiers.
- **Served-model verification:** Requests configured `gpt-6.2-sol` through a local relay; `codex exec --json` logs do not record upstream response model IDs, so the served model is not independently attested in the JSONL artifacts.
- **Sample size & target scale:** `n=3` per `(target, variant)` pair with a single prompt per target on 5 small standalone official showcase fixtures (`54 B` to `12 KB` unhardened).
- **Stage-1 CLI scope only:** Only single-artifact `bla defend` hardening was tested; Stage-2 host-agent source weaving and cross-artifact entanglement were not evaluated.

## License

No license yet.
