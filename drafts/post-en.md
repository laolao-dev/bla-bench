# Measuring BLA v3.6.0 Under Codex CLI + REA (5 Official Samples, n=3): 1.18×–3.58× Net Token Multiplier, 0% Interception

We ran an isolated, reproducible container benchmark of **BLA (`qybaihe/bla` v3.6.0)** to compare its modeled REA-only cost projections against metered token usage when a shell-capable coding agent is allowed to work around REA failures.

## Experimental Scope

All findings below apply specifically **under this experimental setup (Codex CLI + REA, single prompt, 5 samples, `n=3` each)**:

- **Pinned stack**: BLA `3.6.0` (`8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`, `bla defend --intensity bankrupt --seed bla-benchmark-showcase-v1`), `@openai/codex@0.171.0` (`gpt-6.2-sol`, `model_reasoning_effort = "low"`), `rea-agents@6.4.0`.
- **Clean container isolation**: The runtime image (`bla-bench:local`) removes `/opt/bla`, all test/oracle scripts, and all unhardened fixtures, with host-side log capture so `/bench/runs` is never mounted inside the runtime container (`evidence/isolation_check.txt`). Empty-load baseline = `11,092` input tokens (`3/3` runs).
- **Modeled vs. measured threat model**: BLA's published `152.5×–4,817.7×` figures estimate the cost for an agent **relying solely on REA**, whereas our benchmark measures a coding agent **permitted to bypass REA** using standard local Python/Node/shell inspection once REA rejects an artifact.
- **Gate split**: 4 of 5 targets score `92–93/100`; `sqlite-db` scores `68/100` in stock SQLite mode (**below BLA's default `70/100` defense-score gate**, emitted via `--fail-under 0`), so results are reported for both groups.

## Clean-Container Results (`n=3` Medians, Baseline Deducted)

| Target | Format | BLA Score & Gate | `original` Median In | `hardened` Median In | **Measured Net Multiplier** | BLA Modeled (REA-Only) | `hardened` Interception |
|---|---|---|---:|---:|---:|---:|---:|
| `dx-ball` | `.js` | 92/100 (pass) | 174,454 | 383,837 | **2.28×** | 4,817.7× | 0/3 (0%) |
| `notion-electron` | `.asar` | 92/100 (pass) | 177,814 | 605,141 | **3.56×** | 2,532.3× | 0/3 (0%) |
| `license-guard` | `.js` | 92/100 (pass) | 177,953 | 608,792 | **3.58×** | 4,817.7× | 0/3 (0%) |
| `wasm-core` | `.wasm` | 93/100 (pass) | 198,641 | 359,023 | **1.86×** | 381.5× | 0/3 (0%) |
| `sqlite-db`* | `.sqlite` | 68/100 (below default 70 gate) | 171,631 | 200,255 | **1.18×** | 152.5× | 0/3 (0%) |

- **Gate-Passing Group (4 samples, score ≥ 70)**: **`1.86×–3.58×`** net input token multiplier (median **`2.92×`**), **`0/12 (0.0%)`** interception rate.
- **All-Samples Group (5 samples, including `sqlite-db` at 68/100)**: **`1.18×–3.58×`** net input token multiplier (median **`2.28×`**), **`0/15 (0.0%)`** interception rate.

## JSONL Evidence of Direct Artifact Parsing

In every hardened run where REA's static analyzer rejected the target, Codex pivoted immediately to targeted local parsing:
- `dx-ball`: `runs/20261127T035024721349+0000_dx-ball_hardened.jsonl#L9` (`rea.analyze_javascript_application` failed) → `#L11` (`rg`/`head`/`tail` slicing `original/*.js`);
- `notion-electron`: `runs/20261127T035709869570+0000_notion-electron_hardened.jsonl#L7` (REA rejected 24.7 MB ASAR header) → `#L9` (`python` `struct.unpack('<4I', f.read(16))` reading the ASAR Pickle header);
- `license-guard`: `runs/20261127T040459701592+0000_license-guard_hardened.jsonl#L7` → `#L9` (`head`/`tail` slicing `original/license-validator.js`);
- `wasm-core`: `runs/20261127T041225208013+0000_wasm-core_hardened.jsonl#L7` → `#L13` (`xxd`/`strings`/`node` `WebAssembly.Module` section parsing);
- `sqlite-db`: `runs/20261127T041448976791+0000_sqlite-db_hardened.jsonl#L7` → `#L9` (`python` `sqlite3.connect` inspecting `sqlite_schema`).

Under this experimental setup (Codex CLI + REA, single prompt, 5 samples, `n=3`), BLA reliably trips REA's default static budgets and increases JS/ASAR wall-clock time ~6×, while an agent allowed to bypass REA with local scripts reconstructs all 5 targets (`12/12` test cases each) at `1.18×–3.58×` net token cost.
