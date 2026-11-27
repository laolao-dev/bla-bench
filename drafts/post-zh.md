# 在隔离容器中实测 BLA v3.6.0（Codex CLI + REA MCP）：达标样本净增 Token 1.86×–3.58×（中位数 2.92×），拦截率 0/12

近期在严格隔离的 Docker 容器中，对反 AI 逆向开源项目 **BLA（[qybaihe/bla](https://github.com/qybaihe/bla) v3.6.0）** 做了一组可复现对照测试，测量其 `bankrupt` 档位单产物加固在面对通用 Coding Agent 时的真实 token 消耗、耗时变化与逻辑还原准确率。

先说正面的实测观察：**在全部 `15/15` 次加固样本运行中，REA 的默认静态分析均按预期被拦下**（`14/15` 次触发静态分析器显式报错或预算拒绝，另有 `1/15` 次 `sqlite-db` 运行跳过静态工具、改由 REA 自身的动态进程捕获工具执行），且 **JS 与 Electron ASAR 样本的中位逆向耗时从 `59.6s–78.8s` 拉长至 `404.7s–463.9s`（增加约 `5.7×–6.8×`）**。

## 1. 实验设置与评估口径

以下结果严格限定**在本实验设置下（Codex CLI + REA MCP，每个样本单一提示词，5 个官方样本，每种条件 `n=3`）**：

- **组件版本与模型配置**：
  - BLA：`qybaihe/bla` `v3.6.0`（锁定提交 `8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`），加固命令 `bla defend <input> -o <output> --intensity bankrupt --seed bla-benchmark-showcase-v1 --fail-under 0 --json`（注：`--fail-under 0` 仅影响评分 `68/100` 的 `sqlite-db`，其余 4 个样本评分为 `92–93/100`，本身已超过默认 `70/100` 门槛）。
  - Agent：`@openai/codex@0.171.0`（`requested model: gpt-6.2-sol (served via a local relay; served model not independently verified)`，`model_reasoning_effort = "low"`，`wire_api = "responses"`）。
  - MCP 服务：`rea-agents@6.4.0`（`mcp_servers.rea.default_tools_approval_mode = "approve"`）。
- **容器隔离与空载基线**：多阶段构建的纯净运行镜像（非 root `uid=10001`，`--cap-drop ALL`，`--internal` 内网 + 模型端口字节转发）不含 `/opt/bla` 源码、不含测试/判分脚本、不挂载历史 `runs/` 日志（全盘可读文件核验见仓库 `evidence/isolation_check.txt`）；等价性判分在独立的 `--network none` 验证容器中对 12 组输入实跑比对。空载基线实测 3 次恒为 `11,092` input tokens，计算净增倍数时先行扣除。
- **与 BLA 官方估算的口径差异**：据我们对 `bla benchmark`（`token-estimator.ts`）的理解，作者给出的倍数估算的是**「Agent 仅依赖 REA 静态分析管道」**时的理论开销；而本实验测量的是**「具备常规 Linux 命令行环境的 Coding Agent 在 REA 受阻后，被允许回退到本地 Python/Node/Shell 脚本直接解析产物」**时的实际开销。

## 2. 纯净容器实测结果（`n=3` 中位数，已扣除基线 `11,092`）

| 样本 | 格式 | BLA 评分与默认门槛 | `original` 中位数 Input | `hardened` 中位数 Input | 中位耗时（`orig` → `hard`） | **实测净增倍数** | BLA 模型估算（仅靠 REA） | `hardened` 拦截率 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `dx-ball` | `.js` | `92/100`（达标） | 174,454 | 383,837 | 59.6s → 404.7s | **2.28×** | 4,817.7× | **0/3 (0%)** |
| `notion-electron` | `.asar` | `92/100`（达标） | 177,814 | 605,141 | 78.8s → 463.9s | **3.56×** | 2,532.3× | **0/3 (0%)** |
| `license-guard` | `.js` | `92/100`（达标） | 177,953 | 608,792 | 75.9s → 434.6s | **3.58×** | 4,817.7× | **0/3 (0%)** |
| `wasm-core` | `.wasm` | `93/100`（达标） | 198,641 | 359,023 | 63.4s → 101.5s | **1.86×** | 381.5× | **0/3 (0%)** |
| `sqlite-db`* | `.sqlite` | `68/100`（未达默认 70 门槛） | 171,631 | 200,255 | 62.8s → 79.5s | **1.18×** | 152.5× | **0/3 (0%)** |

- **达标样本组（4 个样本，加固评分 `92–93/100` ≥ 70）**：实测净增 input token 倍数为 **`1.86×–3.58×`（中位数 `2.92×`）**，功能拦截率为 **`0/12 (0.0%)`**（每次运行均通过 `12/12` 用例校验）。
- **补充参考（含未达默认门槛的 `sqlite-db`，共 5 个样本）**：`sqlite-db` 在保留标准 SQLite 客户端与 `PRAGMA integrity_check` 兼容性的默认模式下评分上限为 `68/100`；合并全部 5 个样本时倍数为 `1.18×–3.58×`（中位数 `2.28×`），拦截率 `0/15 (0.0%)`。

## 3. 日志观察：REA 触发预算限制后的行为路径

在 `14/15` 次加固运行中，REA 静态分析工具按设计触发体积或复杂度限制返回错误后，Codex 立即改用本地脚本针对性拆解 `./original/*`（如 `head`/`tail`/`rg` 切片定位导出函数、`struct.unpack('<4I', f.read(16))` 直接读取 24.7 MB ASAR Pickle 头部、Python/Node 解析 Wasm 自定义节后核心代码段、`sqlite3.connect` 检查 `sqlite_schema` 排除蜜罐表）；余下 `1/15` 次（`sqlite-db` 第 2 轮）则是由 REA 自身的 `rea.capture_process_scenario` 调用 `python3 sqlite3` 完成查询（不计作绕过 REA）。在我们的运行中，单产物 `bla defend` 有效阻断了默认 REA 静态通道并显著增加了 JS/ASAR 耗时，但尚未阻止具备 Shell 权限的 Agent 还原这类小型独立函数。

## 4. 局限说明

- **单一 Agent 框架**：仅测试了容器内启用常规 Shell 的 `@openai/codex@0.171.0`；若运行环境禁止任意脚本执行、强制只能调用 MCP 工具，结果会完全不同。
- **推理档位与模型核验**：全程使用 `model_reasoning_effort = "low"`（低档位下仍 `12/12` 还原使“未拦截”这一观察更稳健，但高推理档位下的 token 倍数可能不同）；同时 `codex exec --json` 未记录上游返回模型名，实际服务模型未由日志独立验证。
- **样本规模与次数**：每种条件 `n=3`、单一提示词，且被测对象均为体积较小的官方独立 showcase 样本（原件 `54 B–12 KB`）。
- **仅覆盖 Stage-1 CLI**：仅测试了单步 `bla defend` 产物加固，未测试 Stage-2 宿主 Agent 源码编织（source weaving）与跨产物耦合（cross-artifact entanglement）。
- **两轮隔离核验披露**：首轮运行存在容器静态隔离不完整问题（经逐行核查 JSONL 确认实际越界读取为 `0/15`）；修复多阶段纯净镜像后重跑了全部 15 次加固实验，达标组中位数由 `2.67×` 变为 `2.92×`，拦截率同为 `0%`，结论一致。

## 5. 复现仓库与上游反馈

- 完整复现脚本、Dockerfile、脱敏 JSONL 原始日志与等价性测试：https://github.com/laolao-dev/bla-bench
- 已同步提交给上游作者讨论的数据报告：[qybaihe/bla#319](https://github.com/qybaihe/bla/issues/319)（另附实测准备期间发现的 `Vault.evm` 跳转偏移问题反馈：[qybaihe/bla#320](https://github.com/qybaihe/bla/issues/320)）
