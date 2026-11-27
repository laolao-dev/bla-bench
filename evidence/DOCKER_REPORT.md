# BLA 实测迁入 Docker：报告

日期：2026-11-25（JST）。范围：Docker 体检 → 锁版本 → 构建 → 容器内离线检查 → 真实 Codex 运行。
未 push、未建远程仓库、未改本机全局配置；新增现金 0 日元。

真实运行共 3 次：原计划 2 次，你批准后加了第 3 次。

1. 空载基线。
2. dx-ball 第一次：REA 分析器因镜像缺 `ps` 失败。
3. dx-ball 第二次：补上 procps，同时加了出网限制。

**以第 3 次作为 docker 的正式结果。**

## 结论

| 项 | 结果 |
|---|---|
| Docker | 可用。Engine 起初没运行，正常启动一次 Docker Desktop 后可用；`hello-world` 通过（`evidence/docker-health.txt`） |
| BLA 官方 benchmark（容器内） | 16/16 runtime checks passed（最终镜像上复验） |
| 项目测试（容器内） | 6/6 OK |
| 一致性脚本自检（本机 answer.py 对原 JS，容器内） | 12/12 |
| 空载基线（docker） | input 11,092（cached 3,968），output 8，3.9 s，0 次工具调用 |
| dx-ball original（docker，正式） | input 192,082（cached 159,488），output 2,184，81.8 s，REA 1 次成功，answer 12/12 |

## 版本（全部写死在 Dockerfile）

| 组件 | 版本 / 固定方式 |
|---|---|
| 基础镜像 | `python:3.12.16-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64`（Debian 12.15） |
| Node 运行时 | 从 `node:24.22.2-bookworm-slim@sha256:01d566e8d94d8c619591d78652babfccd3c6992a3dffa9ed5ab39e11cf6c70e9` 复制；node v24.22.2，npm 11.19.1 |
| Python | 3.12.16 |
| Codex CLI | `@openai/codex@0.171.0`（npm integrity `sha512-1IOFzL2X…qk2Eg==`） |
| REA | `rea-agents@6.4.0`，全局预装（integrity `sha512-Vj1zWfSl…k8LTWEQ==`）；本机用 `npx -y rea-agents@6.4.0` |
| BLA | `qybaihe/bla@8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`（bla-agents 3.6.0），构建时断言 HEAD，`npm ci` 按 lockfile 安装 |
| apt | git 2.39.5、ca-certificates、procps。没有按版本号锁定，当次的实际内容由镜像 ID 固定 |
| 模型 | `gpt-6.2-sol`，reasoning effort `low`，provider `cpa-gui`（本机代理），与本机一致 |

**最终镜像**：`bla-bench:local`，image ID `sha256:db5491b3504b167bbde8ff19538b3562abf818bc37dc7eb3c8c513cb3c74996f`，
349,146,819 字节，运行用户 `bench`（uid 10001）。镜像只在本地，没有 registry RepoDigest，image ID 就是内容 digest。
第一次 dx-ball 和空载基线用的是上一版镜像 `sha256:8dd168c4…70e9`：没有 procps，直连 `host.docker.internal`。

## host 与 docker 对比（dx-ball / original）

| 指标 | host（14:25 JST） | docker 正式（17:10 JST） | 差异 | docker 第一次（16:52，缺 ps，仅参考） |
|---|---:|---:|---|---:|
| input tokens | 250,254 | 192,082 | −58,172（−23.2%） | 175,461 |
| cached input | 202,240 | 159,488 | −42,752 | 151,552 |
| 非缓存 input | 48,014 | 32,594 | −32.1% | 23,909 |
| output tokens | 2,283 | 2,184 | −4.3% | 1,512 |
| 耗时 | 82.7 s | 81.8 s | −0.9 s | 70.0 s |
| REA 调用 | 1：`analyze_javascript_application` 成功 | 1：`analyze_javascript_application` 成功 | **一致** | 2（analyze 失败 + open_binary） |
| shell 命令 | 6（PowerShell，3 次 apply_patch 转义重试） | 5（bash：`rg`、`apply_patch` 不存在，改用 heredoc 写文件） | 相近 | 4 |
| 直接读源码 | 是（`Get-Content original/…js`） | 是（`nl -ba original/…js`） | 相同 | 是 |
| answer.py 与原 JS | 12/12 | 12/12 | 相同 | 12/12 |
| `valid` | True | True | | True |

空载基线：docker 11,092 input / 8 output。本机没有测过同配置的空载基线（14:09 的 181,696 是失败运行，只能当参考）。
docker 正式结果扣除基线后，dx-ball 净增 180,990 input tokens。

原始数据：
- 空载基线：`runs/20261125T075217692604+0000_baseline_baseline.jsonl`
- dx-ball 正式：`runs/20261125T081000147134+0000_dx-ball_original.jsonl`
- dx-ball 第一次：`runs/20261125T075229818390+0000_dx-ball_original.jsonl`

容器生成的答案在 `evidence/docker-dx-ball-answer/`（正式）和 `evidence/docker-dx-ball-answer-run1/`。

## 偏差及原因

1. **第一次 dx-ball 时 REA 分析器起不来（已修）。** 报错：`Linux process ownership inspection requires a procps-compatible ps on REA's PATH before launching a child: spawn ps ENOENT`。
   在 Dockerfile 里加了 `procps`。跑真实运行前，先在断网容器里直接执行 `rea-agents analyze-javascript-application`，确认能正常出 evidence，没有经过模型。
   第 3 次运行时，REA 路径和本机一致。
   `run_once.py` 的失败正则不匹配 `capability_unavailable`，所以第一次仍被判为 valid。建议以后把它判为 invalid，这次没改。
2. **沙箱模式不同。** 容器里的 bwrap 无法创建 user namespace（`evidence/preflight-sandbox-error.txt`），`-s workspace-write` 下 agent 的命令会全部失败。
   改为由环境变量 `BLA_CODEX_SANDBOX` 决定：本机默认仍是 workspace-write，镜像内设为 `danger-full-access`，由容器本身充当沙箱。
   没有用 `--privileged`、`seccomp=unconfined`，也没有开放 userns。
3. **出网限制（对应安全审查）。** `danger-full-access` 下 agent 的命令能读取只读挂载的 auth.json。为防止它把凭据送出去，真实运行改在 `--internal` 网络 `bla-internal` 里进行：
   唯一出口是中继容器 `bla-relay`（`scripts/relay.py`，只转发字节到 `host.docker.internal:8317`）。
   已验证：经中继访问代理返回 401；直连宿主、`https://example.com`、`1.1.1.1:443` 都被挡住。一致性检查改用 `--network none`。
   剩余风险：agent 仍能读到 auth.json，并把它发给本机模型代理本身。代理本来就持有这个密钥，所以这不算新的暴露面。
4. **token 仍比本机少 23%（推断，n=1）。** 本机 Codex 还挂着 chrome-devtools、context7、node_repl、cua_repl、personal_context、sister_memory 等 MCP，以及多个插件、skills、全局 AGENTS.md 和 memories。
   容器只有 REA，memories 关闭，所以固定开销更小，但本机侧没有单独测过，无法精确拆分。
   output 和耗时与本机基本一致（−4%、−1 s），说明 agent 做的工作量相当。
5. **空载基线是在上一版镜像上测的**：没有 procps，网络直连。基线没有调用任何工具，网络路径也不影响 token 计数，所以我判断它对新镜像同样适用，但没有重测。
6. **时间戳时区**：容器内是 UTC（`+00:00`），本机是 JST（`+09:00`）。
7. **12 组输入是重新定义的**：仓库里没有之前「12/12」所用输入的记录。`scripts/check_equiv.py` 新定义了 12 组（含钳位、零宽、int32 回绕、小数），本机答案和容器两份答案都是 12/12。

## 凭据与隔离

- 镜像层、构建日志、git、报告里都没有密钥：提交前按本机密钥原值扫描了全部受控文件，命中 0。
- `auth.json` 和模型目录只在 `docker run` 时 `readonly` 挂载。容器内写入会报 `Read-only file system`。
- 容器使用自己写的最小配置 `docker/codex-config.toml`，没有复制本机 `config.toml`。provider 用 `requires_openai_auth = true` 读取挂载的 auth.json。
  在容器内用假端点验证过：请求带 Bearer，长度 67，与本机一致；只打印了长度，没打印值。
- 挂载只有：`results.csv`、`runs/`、`docker-work/targets/<样本>`（每次重建，只含 `original/`），以及两份只读凭据/目录文件。
- 容器参数：`--rm --cap-drop ALL --security-opt no-new-privileges`，非 root；真实运行在 `--internal` 网络里进行。

## 回滚

```powershell
docker rm -f bla-relay
```
```powershell
docker network rm bla-internal
```
```powershell
docker image rm bla-bench:local
```

然后删除新增文件：`Dockerfile`、`.dockerignore`、`run-docker.ps1`、`docker/`、`scripts/`、`docker-work/`、`evidence/`、
`README.md`、`prompt-baseline.txt`、`targets/baseline/`。也可以直接 `git checkout 9ab2d0f -- .`（迁移前的备份 commit）。
`run_once.py` 和 `results.csv` 要一起还原，否则 `env` 列的表头校验会报错。
基础镜像可按需删除：`docker image rm node:24.22.2-bookworm-slim python:3.12.16-slim-bookworm python:3.12-slim-bookworm hello-world`。
Docker Desktop 可以照常退出。
