# bla-bench 项目上下文

> 本文件供 Antigravity（工作区规则，始终生效）和 Codex 共同读取。
> 内容整理自本仓库的 README.md、NOTES.md、samples.md、evidence/DOCKER_REPORT.md、git log 和目录结构（2026-11-25）。
> 标"待确认"的地方是仓库里没有写明的，不要当成事实。

## 项目是做什么的

用 Codex CLI + REA MCP（`rea-agents`）对 BLA 官方未加固样本做单次实测，记录 token、耗时、REA 调用次数和答案正确性。

- 被测对象：BLA（`qybaihe/bla`，bla-agents 3.6.0，固定提交 `8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`）。
- 样本：BLA `src/engine/benchmark.ts` 里的 16 个案例，用 `protectTarget` 之前的原始构造代码重新生成的持久副本（见 `samples.md`）。
- 目前实测的只有最小的 JavaScript 样本 dx-ball（403 字节）。
- 任务提示词：`prompt.txt`（用 REA 分析 `./original`，写出等价 Python 到 `answer.py`，在 `answer.md` 说明依据）；空载基线提示词：`prompt-baseline.txt`。

## 当前进度（截至 commit c1ccb30，2026-11-25 17:12 JST）

- 本机（host）运行：2 次 dx-ball。14:09 那次无效（REA 审批被 `approval_policy=never` 拦截 + node_repl 故障），只能当空载参考；14:25 那次有效，answer 12/12。
- 已迁入 Docker：`Dockerfile` + `run-docker.ps1`，容器内离线检查通过（BLA 官方 benchmark 16/16、项目测试 6/6、一致性自检 12/12）。
- Docker 正式结果（第 3 次运行）：dx-ball input 192,082 / output 2,184 / 81.8 s，REA 1 次成功，answer 12/12；空载基线 input 11,092。
- 所有结果在 `results.csv`（`env` 列区分 `host` / `docker`）。详细对比和偏差说明见 `evidence/DOCKER_REPORT.md`。
- 后续计划（下一个样本、是否扩到 16 项全测等）：**待确认**，仓库里没有写。

## 已定的决定

- **版本全部写死在 `Dockerfile`**：基础镜像 digest、BLA commit、Codex CLI `@openai/codex@0.171.0`、REA `rea-agents@6.4.0`。
- **模型**：`gpt-6.2-sol`，reasoning effort `low`，provider `cpa-gui`（本机代理 `127.0.0.1:8317`）。容器配置在 `docker/codex-config.toml`。
- **REA 审批只对本次进程生效**：`run_once.py` 用 `-c 'mcp_servers.rea.default_tools_approval_mode="approve"'`，不改全局配置、不提权（理由见 `NOTES.md`）。
- **有效性判定**：超时、非零退出码、或 MCP 失败文本显示审批/权限/环境故障 → `valid=False`。`answer_exists` 只说明文件生成了，不代表等价。
- **空载基线要单独测并扣除**；14:09 那次 181,696 不是已分解的实测。
- **凭据不进镜像**：`auth.json` 和模型目录只在 `docker run` 时只读挂载；容器不复制本机 `config.toml`。
- **出网隔离**：真实运行在 `--internal` 网络 `bla-internal` 里，唯一出口是中继容器 `bla-relay`（`scripts/relay.py`）→ 本机模型代理；复用该网络前校验 `Internal=true`。
- **容器内沙箱**：bwrap 起不来，所以镜像内 `BLA_CODEX_SANDBOX=danger-full-access`，由容器本身做隔离；本机仍是 `workspace-write`。
- 未落实的建议：`run_once.py` 的失败正则不匹配 `capability_unavailable`，报告建议以后判为 invalid，**当时没改**（是否要改：待确认）。

## 常用命令

```powershell
.\run-docker.ps1                    # 构建 + 离线检查 + 空载基线 + dx-ball
.\run-docker.ps1 -Stage check       # 只构建和离线检查，不调用模型
.\run-docker.ps1 -Stage baseline    # 或 -Stage dx-ball
python run_once.py --target targets\dx-ball --label original   # 本机方式
python -m unittest discover -s tests
```

## 目录说明

| 路径 | 内容 |
|---|---|
| `run_once.py` | 跑一次 `codex exec --json`，把 token / 有效性写进 `results.csv` |
| `run-docker.ps1`、`Dockerfile`、`.dockerignore` | Docker 构建与运行入口 |
| `docker/` | 容器专用 `codex-config.toml`、`entrypoint.sh` |
| `scripts/` | `check_equiv.py`（12 组输入对照 answer.py 与原 JS）、`inspect_run.py`（汇总 JSONL）、`relay.py`（出网中继） |
| `tests/` | 项目单测（6 项） |
| `fixtures/` | 16 个 BLA 原始样本（清单见 `samples.md`） |
| `targets/` | 每个样本的运行目录（`original/` + 生成的 `answer.py` / `answer.md`）；`baseline/` 是空载基线占位 |
| `runs/` | 每次运行的原始 JSONL 和 stderr |
| `results.csv` | 汇总结果 |
| `evidence/` | Docker 迁移报告、构建/检查日志、容器生成的答案 |
| `logs/` | 迁移前本机阶段的日志（clone、构建、benchmark、preflight 等） |
| `tmp/` | 重新生成原始样本的脚本（`materialize-originals.mjs`、`original-builders.mjs`） |
| `bla/` | 第三方 BLA 仓库，独立 git，固定提交，已被 `.gitignore` 排除；它有自己的 `AGENTS.md` |
| `docker-work/` | 容器运行时工作区，每次重建，已忽略 |
| `npm-cache/` | npm 缓存，已忽略 |

## 回滚点

`git checkout 9ab2d0f -- .` 回到 Docker 迁移前；`run_once.py` 和 `results.csv` 要一起还原。其余回滚步骤见 README 和 DOCKER_REPORT。
