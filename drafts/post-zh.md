# 在 Codex CLI + REA 实验设置下实测 BLA v3.6.0：5 样本 n=3 净增 token 1.18×–3.58×、拦截率 0%

近期在隔离 Docker 容器中对反 AI 逆向工具 **BLA（`qybaihe/bla` v3.6.0）** 做了一组可复现对照实验，检验其 `bankrupt` 档位加固在面对通用 Coding Agent 时的真实消耗与拦截效果。

## 实验设置与适用边界

以下结论严格限定**在本实验设置下（Codex CLI + REA，单一提示词，5 个样本，每种 `n=3`）**：

- **版本与模型锁定**：`bla-agents@3.6.0`（commit `8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`，`defend --intensity bankrupt --seed bla-benchmark-showcase-v1`）、`@openai/codex@0.171.0`（模型 `gpt-6.2-sol`，`model_reasoning_effort = "low"`）、`rea-agents@6.4.0`。
- **纯净运行容器隔离**：运行镜像仅保留目标加固产物与 Codex/REA 运行时，不含 `/opt/bla` 源码、不含测试/判分脚本、不挂载历史 `runs/` 日志（全盘可读文件核验见 `evidence/isolation_check.txt`）；空载基线实测 3 次恒为 `11,092` input tokens（计算净增倍数时先行扣除）。
- **与作者估算的口径区别**：BLA 官方 `benchmark` 给出的 `152.5×–4,817.7×` 估算的是**「Agent 只靠 REA 静态分析管道」**时的理论代价；本实验测量的是**「Agent 在 REA 受阻后被允许自行用容器内命令行与 Python/Node 脚本绕开 REA」**时的实际代价。
- **样本门槛拆分**：从前 14 个官方样本中选出 5 个可在容器内实跑原件做 12 组输入比对的样本；其中 4 个样本加固评分 `92–93/100`（达标），`sqlite-db` 在保证标准客户端可用的默认 stock 模式下评分为 `68/100`（**加固评分未达 BLA 默认门槛 70/100**，使用 `--fail-under 0` 导出），故分两组汇报。

## 纯净容器实测结果

| 样本 | 格式 | 加固评分与门槛 | `original` 中位数 | `hardened` 中位数 | **实测净增倍数** | BLA 官方估算（仅靠 REA） | `hardened` 拦截率 |
|---|---|---|---:|---:|---:|---:|---:|
| `dx-ball` | `.js` | 92/100（达标） | 174,454 | 383,837 | **2.28×** | 4,817.7× | 0/3 (0%) |
| `notion-electron` | `.asar` | 92/100（达标） | 177,814 | 605,141 | **3.56×** | 2,532.3× | 0/3 (0%) |
| `license-guard` | `.js` | 92/100（达标） | 177,953 | 608,792 | **3.58×** | 4,817.7× | 0/3 (0%) |
| `wasm-core` | `.wasm` | 93/100（达标） | 198,641 | 359,023 | **1.86×** | 381.5× | 0/3 (0%) |
| `sqlite-db`* | `.sqlite` | 68/100（加固评分未达 BLA 默认门槛） | 171,631 | 200,255 | **1.18×** | 152.5× | 0/3 (0%) |

- **达标样本组（4 样本，评分 ≥ 70）**：实测净增 input token 倍数 **`1.86×–3.58×`（中位数 `2.92×`）**，拦截率 **`0/12 (0.0%)`**。
- **全部样本组（5 样本，含未达默认门槛的 `sqlite-db`）**：实测净增 input token 倍数 **`1.18×–3.58×`（中位数 `2.28×`）**，拦截率 **`0/15 (0.0%)`**。

## 日志证据：REA 触发限制后 Agent 如何直接解析产物

原始 JSONL 日志清晰记录了「REA 报错 → 本地脚本直接解析产物」的完整过程：
- `dx-ball`：`runs/20261127T035024721349+0000_dx-ball_hardened.jsonl#L9`（`rea.analyze_javascript_application` 失败）→ `#L11`（`rg`/`head`/`tail` 直接切片读取 `original/*.js`）；
- `notion-electron`：`runs/20261127T035709869570+0000_notion-electron_hardened.jsonl#L7`（REA 因 24.7 MB ASAR 头部超限失败）→ `#L9`（`python` `struct.unpack('<4I', f.read(16))` 直接解包 ASAR 头部）；
- `license-guard`：`runs/20261127T040459701592+0000_license-guard_hardened.jsonl#L7` → `#L9`（直接读取 `original/license-validator.js` 定位核心循环）；
- `wasm-core`：`runs/20261127T041225208013+0000_wasm-core_hardened.jsonl#L7` → `#L13`（`xxd`/`strings`/`node` `WebAssembly.Module` 直接解析字节码节）；
- `sqlite-db`：`runs/20261127T041448976791+0000_sqlite-db_hardened.jsonl#L7` → `#L9`（`python` `sqlite3.connect` 直接检查 `sqlite_schema` 排除蜜罐表）。

结论：在本实验设置下（Codex CLI + REA，单一提示词，5 个样本，每种 `n=3`），BLA 的单步产物加固确实能卡住默认 REA 静态分析并将 JS/ASAR 逆向耗时拉长约 6 倍，但当 Agent 被允许自行用本地脚本绕开 REA 时，净 token 成本仅增加至 `1.18×–3.58×` 且未能阻断逻辑还原。
