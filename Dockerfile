# syntax=docker/dockerfile:1
# BLA 实测的可复现多阶段环境：
# - verifier 阶段（bla-bench:verifier）：仅用于离线自检、生成加固样本、运行等价性检查与无状态 TCP 中继。
# - runtime  阶段（bla-bench:local，默认最终镜像）：给 Codex + REA 运行的纯净沙箱镜像，
#   不含 /opt/bla、不含 /bench/tests、不含 /bench/scripts、不含 /bench/fixtures、不含历史日志。

# ---- 版本锁 ----
# Node 24.22.2 / Python 3.12.16，均按 digest 固定（2026-11-25 拉取）
FROM node:24.22.2-bookworm-slim@sha256:01d566e8d94d8c619591d78652babfccd3c6992a3dffa9ed5ab39e11cf6c70e9 AS node
FROM python:3.12.16-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64 AS base

ARG CODEX_VERSION=0.171.0
ARG REA_VERSION=6.4.0

# Node 运行时直接取自官方 node 镜像（同一 digest）
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && node --version && npm --version

# git 供 verifier 阶段拉取固定 commit 的 BLA；procps 提供 REA 进程归属检查所需的 ps
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates procps \
 && rm -rf /var/lib/apt/lists/*

# Codex CLI 与 REA MCP 预装为全局固定版本（容器内不再走 npx 动态下载）
RUN npm install -g --no-fund --no-audit @openai/codex@${CODEX_VERSION} rea-agents@${REA_VERSION} \
 && npm cache clean --force \
 && codex --version

# ---- verifier 阶段：离线检查、生成加固产物、等价性比对、网络中继 ----
FROM base AS verifier

ARG BLA_REPO=https://github.com/qybaihe/bla
ARG BLA_COMMIT=8dcf9858f5c931e26c4d3526b29c8e10a97ec17f

RUN useradd --create-home --uid 10001 --shell /bin/bash bench \
 && mkdir -p /opt/bla /bench /home/bench/.codex \
 && chown -R bench:bench /opt/bla /bench /home/bench/.codex
USER bench

WORKDIR /opt/bla
RUN git clone --quiet ${BLA_REPO} . \
 && git checkout --quiet ${BLA_COMMIT} \
 && test "$(git rev-parse HEAD)" = "${BLA_COMMIT}" \
 && npm ci --no-fund --no-audit \
 && npm run build \
 && npm cache clean --force

WORKDIR /bench
COPY --chown=bench:bench run_once.py prompt.txt prompt-baseline.txt ./
COPY --chown=bench:bench tests ./tests
COPY --chown=bench:bench scripts ./scripts
COPY --chown=bench:bench fixtures/dx-ball ./fixtures/dx-ball
COPY --chown=bench:bench prompts ./prompts
COPY --chown=bench:bench docker/codex-config.toml /home/bench/.codex/config.toml

ENV CODEX_HOME=/home/bench/.codex \
    BLA_BENCH_ENV=docker \
    BLA_CODEX_SANDBOX=danger-full-access \
    PYTHONDONTWRITEBYTECODE=1 \
    NO_UPDATE_NOTIFIER=1

COPY --chown=bench:bench docker/entrypoint.sh /usr/local/bin/bench-entrypoint
ENTRYPOINT ["bash", "/usr/local/bin/bench-entrypoint"]
CMD ["check"]

# ---- runtime 阶段（默认最终镜像 bla-bench:local）：纯净运行容器 ----
FROM base AS runtime

RUN useradd --create-home --uid 10001 --shell /bin/bash bench \
 && mkdir -p /bench /home/bench/.codex \
 && chown -R bench:bench /bench /home/bench/.codex
USER bench

WORKDIR /bench
# 仅放入无密钥的最小 Codex 配置；不含 /opt/bla、tests、scripts、fixtures、runs、results.csv
COPY --chown=bench:bench docker/codex-config.toml /home/bench/.codex/config.toml

ENV CODEX_HOME=/home/bench/.codex \
    BLA_BENCH_ENV=docker \
    BLA_CODEX_SANDBOX=danger-full-access \
    PYTHONDONTWRITEBYTECODE=1 \
    NO_UPDATE_NOTIFIER=1

CMD ["codex", "--version"]
