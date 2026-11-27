# bla-bench

在出网受限且运行文件系统与测试脚本完全隔离的 Docker 容器中，使用 Codex CLI（`@openai/codex@0.171.0`）+ REA MCP（`rea-agents@6.4.0`）对 BLA（`qybaihe/bla` v3.6.0，固定提交 `8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`）官方样本的未加固版（`original`）与 `bankrupt` 加固版（`hardened`）进行对照实测，记录真实 token 消耗、耗时、REA 调用及 12 组输入实跑等价性检查结果。

![BLA v3.6.0 容器实测对比图](evidence/w3_comparison.png)

## 结论

**在本实验设置下（Codex CLI + REA，单一提示词，5 个样本，每种 `n=3`）**，BLA `bankrupt` 加固如预期触发了 REA 默认静态分析预算限制，但被允许使用容器内常规命令行环境的 Agent 在 REA 失败后均自行绕开 REA、改用本地脚本直接解析产物，最终全部还原出等价逻辑——**达标样本组（4 样本，加固评分 92–93/100）实测净增 input token 倍数为 `1.86×–3.58×`（中位数 `2.92×`）、拦截率 `0/12 (0.0%)`；全部样本组（5 样本，含评分 `68/100` 加固评分未达 BLA 默认门槛的 `sqlite-db`）实测净增 input token 倍数为 `1.18×–3.58×`（中位数 `2.28×`）、拦截率 `0/15 (0.0%)`**。需要说明口径差异：**BLA 作者在官方 benchmark 中给出的 `152.5×–4,817.7×` 是静态估算「Agent 只靠 REA 管道分析」时的理论代价，而本仓库测量的是「Agent 在 REA 受阻后被允许自行用脚本绕开 REA」时的实测代价**。

### 第二轮纯净隔离容器实测汇总（空载基线 = `11,092` input tokens，`original` 沿用 15 次，`hardened` 重跑 15 次）

| 样本 | 格式 | 原始 → 加固大小 | BLA 加固评分与门槛状态 | `original` 中位数 input | `hardened` 中位数 input（第二轮） | **我们实测倍数** | BLA 官方估算倍数（仅靠 REA） | `hardened` 拦截率 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `dx-ball` | `.js` | 403 B → 170,886 B | 92/100（达标） | 174,454 | 383,837 | **2.28×** | 4,817.7× | 0/3 (0%) |
| `notion-electron` | `.asar` | 1,769 B → 24,671,339 B | 92/100（达标） | 177,814 | 605,141 | **3.56×** | 2,532.3× | 0/3 (0%) |
| `license-guard` | `.js` | 782 B → 183,188 B | 92/100（达标） | 177,953 | 608,792 | **3.58×** | 4,817.7× | 0/3 (0%) |
| `wasm-core` | `.wasm` | 54 B → 6,880,378 B | 93/100（达标） | 198,641 | 359,023 | **1.86×** | 381.5× | 0/3 (0%) |
| `sqlite-db`* | `.sqlite` | 12,288 B → 49,152 B | 68/100（**加固评分未达 BLA 默认门槛**，`--fail-under 0`） | 171,631 | 200,255 | **1.18×** | 152.5× | 0/3 (0%) |

- `*` **`sqlite-db` 门槛说明**：SQLite 样本在保持标准客户端与 `PRAGMA integrity_check` 可用的默认 stock 模式下，BLA 诚实评分上限为 `68/100`，低于 `bla defend` 默认门槛 `minDefenseScore = 70`（启用 `--sqlite-eval-trap` 会破坏标准 SQLite 连接），因此加固时传入 `--fail-under 0` 并单独标注「加固评分未达 BLA 默认门槛」。
- **「直接解析产物」的 JSONL 原始证据位置（第二轮纯净容器运行日志）**：
  - `dx-ball`：`runs/20261127T035024721349+0000_dx-ball_hardened.jsonl#L9`（`rea.analyze_javascript_application` 失败）→ `#L11`（`rg`/`head`/`tail` 直接切片读取 `original/*.js`）；同见 `runs/20261127T041554828409+0000_dx-ball_hardened.jsonl#L7`、`#L9` 与 `runs/20261127T044054517732+0000_dx-ball_hardened.jsonl#L7`、`#L9`。
  - `notion-electron`：`runs/20261127T035709869570+0000_notion-electron_hardened.jsonl#L7`（`rea.analyze_javascript_application` 因 24.7 MB ASAR 头部超限失败）→ `#L9`（`python` `struct.unpack('<4I', f.read(16))` 直接解析 ASAR 头部提取 `main.js`）；同见 `runs/20261127T042252436598+0000_notion-electron_hardened.jsonl#L7`、`#L9` 与 `runs/20261127T044739798280+0000_notion-electron_hardened.jsonl#L7`、`#L9`。
  - `license-guard`：`runs/20261127T040459701592+0000_license-guard_hardened.jsonl#L7`（`rea.analyze_javascript_application` 失败）→ `#L9`（`head`/`tail` 直接读取 `original/license-validator.js`）；同见 `runs/20261127T043043188735+0000_license-guard_hardened.jsonl#L7`、`#L9` 与 `runs/20261127T045511098499+0000_license-guard_hardened.jsonl#L7`、`#L9`。
  - `wasm-core`：`runs/20261127T041225208013+0000_wasm-core_hardened.jsonl#L7`（`rea.inspect_binary_layout` 失败）→ `#L13`（`xxd`/`strings`/`node` `WebAssembly.Module` 直接解析 `original/crypto-core.wasm` 节与字节码）；同见 `runs/20261127T043752250802+0000_wasm-core_hardened.jsonl#L7`、`#L11` 与 `runs/20261127T050224238746+0000_wasm-core_hardened.jsonl#L7`、`#L9`。
  - `sqlite-db`：`runs/20261127T041448976791+0000_sqlite-db_hardened.jsonl#L7`（`rea.open_binary` 失败）→ `#L9`（`python` `sqlite3.connect` 直接只读打开 `original/entitlements.sqlite` 枚举 `sqlite_schema` 筛除蜜罐表）；`runs/20261127T043934344763+0000_sqlite-db_hardened.jsonl#L7`（经 `rea.capture_process_scenario` 调用 `python3 -c "import sqlite3..."` 直接查询数据库）；`runs/20261127T050404617803+0000_sqlite-db_hardened.jsonl#L7`、`#L9`。

## 实验条件

- **容器与网络隔离**：
  - 基础镜像锁定：`python:3.12.16-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64` + `node:24.22.2-bookworm-slim@sha256:01d566e8d94d8c619591d78652babfccd3c6992a3dffa9ed5ab39e11cf6c70e9`（Debian 12，非 root 用户 `bench` `uid=10001`，`--cap-drop ALL --security-opt no-new-privileges`）。
  - 网络隔离：运行容器接入 `--internal` 网络 `bla-internal`（启动前强制校验 `Internal=true`），唯一出口为无状态字节转发容器 `bla-relay` → 宿主机模型代理 `:8317`；等价性检查在 `--network none` 完全断网验证容器 `bla-bench:verifier` 中执行。
  - 文件系统隔离：运行镜像 `bla-bench:local`（`Dockerfile` `runtime` 阶段）不含 `/opt/bla`、`/bench/tests`、`/bench/scripts`、`/bench/fixtures`，运行容器不挂载 `/bench/runs` 或 `results.csv`，仅挂载当前单样本工作区 `/bench/targets/<sample>/original/<产物>` 与只读模型凭据（全盘可读文件核验见 `evidence/isolation_check.txt`）。
- **Agent 与 MCP 版本及参数**：
  - Codex CLI：`@openai/codex@0.171.0`
  - **Codex 模型 ID 与推理强度**：`model = "gpt-6.2-sol"`，`model_reasoning_effort = "low"`，`wire_api = "responses"`，`js_repl = false`，`memories = false`（见 `docker/codex-config.toml`）
  - **REA 版本**：`rea-agents@6.4.0`（唯一启用的 MCP 服务，单次进程传入 `-c 'mcp_servers.rea.default_tools_approval_mode="approve"'`）
  - 单次超时上限：`900` 秒（超时记为无效且不重试；实际 45 次有效实验运行 0 超时）
- **BLA 版本与加固参数**：
  - 仓库与版本：`qybaihe/bla`（`bla-agents@3.6.0`），固定提交 `8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`
  - 加固命令：`node /opt/bla/dist/cli.js defend <input> -o <output> --intensity bankrupt --seed bla-benchmark-showcase-v1 --fail-under 0 --json`（产物 SHA-256 清单见 `evidence/hardening_manifest.json`）
- **提示词原文**：
  - 通用任务提示词（`prompt.txt`，用于 `dx-ball`、`license-guard`、`wasm-core` 的全部 `original` 与 `hardened` 运行）：
    ```text
    Use the REA tools to analyze the artifact in ./original. Determine what its main function computes, write an equivalent Python function to ./answer.py, and explain your evidence briefly in ./answer.md. Do not access files outside this directory.
    ```
  - Electron ASAR 接口对齐单次提示词（`prompts/notion-electron.txt`，`original` 与 `hardened` 相同）：
    ```text
    Use the REA tools to analyze the artifact in ./original. Determine what its Electron main-process IPC module computes, write an equivalent Python function register_handlers(store, ipc_main, fetch_fn=None) to ./answer.py (where store provides .get(key) and .set(key, value), ipc_main provides .handle(channel, handler) for sync or async (event, *args) handlers, and optional fetch_fn(url) replaces global fetch), and explain your evidence briefly in ./answer.md. Do not access files outside this directory.
    ```
  - SQLite 接口对齐单次提示词（`prompts/sqlite-db.txt`，`original` 与 `hardened` 相同）：
    ```text
    Use the REA tools to analyze the artifact in ./original. Determine the genuine business entitlement records stored in this SQLite database, write an equivalent Python function query_entitlements(account_id: str | None = None) -> list[dict] to ./answer.py (returning all genuine business rows ordered by primary key when account_id is None, or the matching business row(s) as dicts mapping column name to value when account_id is a string), and explain your evidence briefly in ./answer.md. Do not access files outside this directory.
    ```
  - 空载基线提示词（`prompt-baseline.txt`）：
    ```text
    Reply with exactly one short sentence confirming you are ready. Do not run any commands, do not call any tools, and do not read or write any files.
    ```

## 两轮结果对比与隔离修复披露

**如实披露**：在第一轮 30 次运行（`evidence/w3_runs.csv`）完成后的发布前自审中发现，当时单阶段镜像内仍留有 `/opt/bla`（含官方 `benchmark.ts` 源码）、`/bench/tests`（含单测参考实现）、`/bench/scripts`、`/bench/fixtures/dx-ball`，且容器挂载了 `/bench/runs` 目录，静态隔离边界并不完整。我们对第一轮全部 15 份 `hardened` 原始 JSONL 逐行核查确认：**Agent 实际越界读取次数为 `0/15`**（所有命令与 MCP 路径均未离开 `/bench/targets/<sample>/`）。为彻底消除静态边界隐患，第二轮将 `Dockerfile` 拆分为验证镜像 `bla-bench:verifier` 与纯净运行镜像 `bla-bench:local`，删去上述全部目录、取消 `/bench/runs` 挂载（宿主机在容器外收集日志），经 `evidence/isolation_check.txt` 全盘核验 `STATUS: CLEAN` 后，在纯净容器中完整重跑了全部 15 次 `hardened`（`evidence/w3_r2_runs.csv`，原版 15 次与空载基线 `11,092` 沿用）。

| 样本 / 分组 | 第一轮 `hardened` 中位数 input | 第二轮 `hardened` 中位数 input | 第一轮实测倍数 | 第二轮实测倍数 | 倍数差值（相对变化） | 第一轮拦截率 | 第二轮拦截率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `dx-ball` | 370,423 | 383,837 | 2.20× | **2.28×** | +0.08× (+3.6%) | 0/3 (0%) | **0/3 (0%)** |
| `notion-electron` | 545,882 | 605,141 | 3.21× | **3.56×** | +0.35× (+10.9%) | 0/3 (0%) | **0/3 (0%)** |
| `license-guard` | 533,595 | 608,792 | 3.13× | **3.58×** | +0.45× (+14.4%) | 0/3 (0%) | **0/3 (0%)** |
| `wasm-core` | 300,269 | 359,023 | 1.54× | **1.86×** | +0.32× (+20.8%) | 0/3 (0%) | **0/3 (0%)** |
| `sqlite-db`*（68/100，未达默认门槛） | 208,006 | 200,255 | 1.23× | **1.18×** | -0.05× (-4.1%) | 0/3 (0%) | **0/3 (0%)** |
| **达标样本组中位数（4 样本）** | — | — | 2.67× | **2.92×** | +0.25× (+9.4%) | 0/12 (0%) | **0/12 (0%)** |
| **全部样本组中位数（5 样本）** | — | — | 2.20× | **2.28×** | +0.08× (+3.6%) | 0/15 (0%) | **0/15 (0%)** |

两轮拦截率均为 `0%`，分组中位数倍数仅相差 `+0.08×`（全部组）/ `+0.25×`（达标组），属于同配置大模型多轮采样的正常波动范围，证实第一轮未发生任何外部信息泄漏，正式结论以第二轮纯净容器数据为准。

## 复现

前提：Windows + Docker Desktop（WSL2 引擎）+ `uv`；本机 `%USERPROFILE%\.codex\auth.json` 与 `cpa-gui-model-catalog.json` 已就绪；模型代理在本机 `127.0.0.1:8317` 运行。

```powershell
# 1. 本地依赖、单测与代码检查
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .

# 2. 构建 verifier / 纯净 runtime 双镜像并执行离线自检与运行容器隔离自检
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-docker.ps1 -Stage check
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-docker.ps1 -Stage isolation-check

# 3. 在断网 verifier 容器内生成锁定种子的 5 个加固样本并校验 SHA-256 清单
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-docker.ps1 -Stage harden

# 4. 在纯净 runtime 容器内重跑 15 次 hardened（宿主收集日志）并更新两轮统计与对比图
uv run python scripts\run_w3_r2.py
uv run python scripts\analyze_w3.py
```

样本筛选与排除理由见 `samples.md`，说明见 `NOTES.md`，早期容器迁移记录见 `evidence/DOCKER_REPORT.md`。
