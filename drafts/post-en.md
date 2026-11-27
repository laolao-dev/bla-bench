# Measuring BLA v3.6.0 in Isolated Containers (Codex CLI + REA MCP): 1.86×–3.58× Net Token Multiplier (Median 2.92×) and 0/12 Interception on Gate-Passing Targets

We ran a reproducible, container-isolated benchmark of **[BLA (`qybaihe/bla` v3.6.0)](https://github.com/qybaihe/bla)** to measure metered token usage, wall-clock delay, and 12-case functional reconstruction accuracy when `bankrupt`-hardened artifacts are analyzed by a general-purpose coding agent.

First, what worked as designed: **REA's default static analysis was stopped across all `15/15` hardened runs** (`14/15` explicit static-analyzer rejections, plus `1/15` `sqlite-db` run where static REA tools were skipped in favor of `rea.capture_process_scenario`), and **hardening increased median wall-clock time on the JS and Electron ASAR targets by `~5.7×–6.8×`** (`59.6s → 404.7s` on `dx-ball`, `75.9s → 434.6s` on `license-guard`, and `78.8s → 463.9s` on `notion-electron`).

## 1. Experimental Setup & Threat-Model Scope

All observations below are scoped to **this experimental setup (Codex CLI + REA MCP, single prompt per target, 5 official targets, `n=3` each)**:

- **Pinned stack**:
  - **BLA**: `qybaihe/bla` `v3.6.0` at commit `8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`, hardened via `bla defend <input> -o <output> --intensity bankrupt --seed bla-benchmark-showcase-v1 --fail-under 0 --json` (`--fail-under 0` only affected `sqlite-db` at `68/100`; the other 4 targets scored `92–93/100` and already passed BLA's default `70/100` gate).
  - **Agent & Model**: `@openai/codex@0.171.0` (`requested model: gpt-6.2-sol (served via a local relay; served model not independently verified)`, `model_reasoning_effort = "low"`, `wire_api = "responses"`).
  - **MCP Server**: `rea-agents@6.4.0` (`mcp_servers.rea.default_tools_approval_mode = "approve"`).
- **Container isolation & baseline**: The stripped runtime image (`bla-bench:local`, non-root `uid=10001`, `--cap-drop ALL`, `--internal` network + TCP relay) contains no `/opt/bla`, no test/oracle scripts, no unhardened fixtures, and no mounted `runs/` history (`evidence/isolation_check.txt`); 12-case functional equivalence runs post-hoc in a `--network none` verifier container. Empty-load baseline = `11,092` input tokens (`3/3` runs), deducted before computing net multipliers.
- **Modeled vs. measured scope**: Our understanding is that BLA's built-in estimator (`bla benchmark` / `token-estimator.ts`) models theoretical token cost when an agent relies exclusively on REA's static analysis pipeline, whereas our benchmark measures a coding agent permitted to fall back to local Python/Node/shell scripts once REA rejects or truncates a hardened artifact.

## 2. Clean-Container Results (`n=3` Medians, Baseline `11,092` Deducted)

| Target | Format | BLA Score & Gate Status | `original` Median In | `hardened` Median In | Median Time (`orig` → `hard`) | **Measured Net Multiplier** | BLA Modeled Estimate (REA-Only) | `hardened` Interception |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `dx-ball` | `.js` | `92/100` (pass) | 174,454 | 383,837 | 59.6s → 404.7s | **2.28×** | 4,817.7× | **0/3 (0%)** |
| `notion-electron` | `.asar` | `92/100` (pass) | 177,814 | 605,141 | 78.8s → 463.9s | **3.56×** | 2,532.3× | **0/3 (0%)** |
| `license-guard` | `.js` | `92/100` (pass) | 177,953 | 608,792 | 75.9s → 434.6s | **3.58×** | 4,817.7× | **0/3 (0%)** |
| `wasm-core` | `.wasm` | `93/100` (pass) | 198,641 | 359,023 | 63.4s → 101.5s | **1.86×** | 381.5× | **0/3 (0%)** |
| `sqlite-db`* | `.sqlite` | `68/100` (below default 70 gate) | 171,631 | 200,255 | 62.8s → 79.5s | **1.18×** | 152.5× | **0/3 (0%)** |

- **Primary result — Gate-Passing Group (4 targets, defense score `92–93/100` ≥ 70)**: **`1.86×–3.58×`** net input-token multiplier (median **`2.92×`**), **`0/12 (0.0%)`** functional interception (`12/12` test cases matched on every run).
- **Additional reference — All 5 Targets (including `sqlite-db` at `68/100` in stock SQLite mode)**: `1.18×–3.58×` net input-token multiplier (median `2.28×`), `0/15 (0.0%)` interception.

## 3. What Happened in the Logs After REA Refusals

In `14/15` hardened runs, REA's static analyzers hit BLA's size or structural limits as intended, and Codex pivoted to targeted local scripts on `./original/*` (slicing JS exports with `rg`/`head`/`tail`, unpacking the 24.7 MB ASAR Pickle header via Python `struct.unpack('<4I', f.read(16))`, parsing Wasm sections in Python/Node, and inspecting `sqlite_schema` via `sqlite3.connect`); in the remaining `1/15` run (`sqlite-db` run 2), REA itself executed the query through `rea.capture_process_scenario` (not counted as bypassing REA). In our runs, single-artifact `bla defend` reliably blocked default REA static passes and slowed JS/ASAR analysis by `~5.7×–6.8×`, while a shell-capable coding agent was still able to recover these small standalone functions.

## 4. Limitations

- **Single agent harness**: Only `@openai/codex@0.171.0` with local container shell access was evaluated; agents restricted strictly to MCP tools without shell execution would hit REA's refusals directly.
- **Reasoning effort (`low`) & served-model metadata**: Running at `model_reasoning_effort = "low"` makes the `0/12` interception observation stronger, though token multipliers could differ at higher reasoning-effort tiers. In addition, `codex exec --json` logs do not record upstream response model IDs, so the served model is not independently verified from the JSONL files.
- **Sample size & fixture scale**: `n=3` per `(target, variant)` pair with a single prompt per target on 5 small standalone showcase fixtures (`54 B–12 KB` unhardened).
- **Stage-1 CLI scope only**: Only standalone `bla defend` hardening was tested; Stage-2 host-agent source weaving and cross-artifact entanglement were not evaluated.
- **Round-1 isolation disclosure & Round-2 clean rerun**: Our initial 30-run pass had incomplete static container isolation (`0/15` out-of-directory reads confirmed by JSONL audit); rebuilding a stripped runtime image and rerunning all 15 hardened runs yielded consistent results (gate-passing median `2.67×` in Round 1 vs. `2.92×` in Round 2; `0%` interception in both).

## 5. Links

- Reproduction scripts, Dockerfiles, sanitized JSONL logs, and equivalence checks: https://github.com/laolao-dev/bla-bench
- Upstream benchmark report: [qybaihe/bla#319](https://github.com/qybaihe/bla/issues/319) (plus a showcase fixture jump-offset bug report: [qybaihe/bla#320](https://github.com/qybaihe/bla/issues/320))
