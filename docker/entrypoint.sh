#!/usr/bin/env bash
# 容器入口。子命令：
#   check                         离线检查：BLA 官方 benchmark、项目测试、host answer 一致性（不调用模型）
#   versions                      打印各组件版本
#   harden                        用 BLA 官方 CLI 生成 5 个样本的 hardened 版本并输出清单
#   baseline                      真实运行：空载基线（需挂载 auth.json）
#   dx-ball                       真实运行：dx-ball original（需挂载 auth.json 与 targets/dx-ball）
#   run-sample <id> <label> [pf]  真实运行任意样本（label: original|hardened）
#   equiv                         对 /bench/targets/dx-ball 做 answer.py 与原 JS 一致性检查
#   equiv-sample <id> [orig_file] 对 /bench/targets/<id> 做 answer.py 与原程序实跑一致性检查
set -euo pipefail
cd /bench

versions() {
  echo "node $(node --version)"
  echo "npm $(npm --version)"
  python --version
  codex --version
  echo "rea-agents $(npm ls -g rea-agents --depth=0 --parseable --long 2>/dev/null | sed -n 's/.*rea-agents@//p' | head -1)"
  echo "bla $(git -C /opt/bla rev-parse HEAD) ($(node -p "require('/opt/bla/package.json').version"))"
  echo "user $(id -un) uid=$(id -u)"
}

case "${1:-check}" in
  versions) versions ;;
  check)
    versions
    echo "== BLA 官方 benchmark =="
    (cd /opt/bla && node dist/cli.js benchmark) | tee /tmp/benchmark.txt
    grep -q "All 16 runtime checks passed" /tmp/benchmark.txt
    echo "== 项目测试 =="
    python -m unittest discover -s tests -v
    echo "== 一致性检查脚本自检（fixture JS 对自身 host answer）=="
    if [ -f /bench/host-answer/answer.py ]; then
      mkdir -p /tmp/eq/original && cp fixtures/dx-ball/dx-ball-sound-pan.js /tmp/eq/original/
      cp /bench/host-answer/answer.py /tmp/eq/answer.py
      python scripts/check_equiv.py /tmp/eq
    else
      echo "跳过：未挂载 host-answer"
    fi
    ;;
  harden)
    python scripts/harden_targets.py /bench/all-fixtures /bench/out-targets /bench/out-evidence/hardening_manifest.json
    ;;
  baseline)
    python run_once.py --target targets/baseline --label baseline --prompt-file prompt-baseline.txt --timeout 300
    ;;
  dx-ball)
    python run_once.py --target targets/dx-ball --label original --timeout 900
    ;;
  run-sample)
    sample="${2:?missing sample}"
    label="${3:?missing label}"
    prompt_file="${4:-prompt.txt}"
    python run_once.py --target "targets/${sample}" --label "${label}" --prompt-file "${prompt_file}" --timeout 900
    ;;
  equiv)
    python scripts/check_equiv.py targets/dx-ball
    ;;
  equiv-sample)
    sample="${2:?missing sample}"
    ref_orig="${3:-}"
    if [ -n "${ref_orig}" ]; then
      python scripts/check_equiv.py "targets/${sample}" --sample "${sample}" --ref-original "${ref_orig}"
    else
      python scripts/check_equiv.py "targets/${sample}" --sample "${sample}"
    fi
    ;;
  relay)
    exec python scripts/relay.py
    ;;
  *) exec "$@" ;;
esac
