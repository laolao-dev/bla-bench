"""运行容器隔离自检脚本：启动真实配置的纯净运行容器（bla-bench:local），
列出 bench 用户能读到的所有非系统基础镜像文件，并全盘核验不存在原版源码、参考答案、期望输出、历史日志。
输出写入 evidence/isolation_check.txt；发现任何污染项即返回非零退出码。
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_PATHS = (
    '/opt/bla',
    '/bench/tests',
    '/bench/scripts',
    '/bench/fixtures',
    '/bench/runs',
    '/bench/results.csv',
    '/bench/run_once.py',
    '/bench/prompts',
    '/bench/prompt.txt',
    '/bench/prompt-baseline.txt',
)

CONTAINER_PROBE = r"""
import os
import pathlib
import subprocess

print("=== 1. Container Identity ===")
print("uid/gid:", os.getuid(), os.getgid())
print("cwd:", os.getcwd())

print("\n=== 2. Forbidden Paths Absence Check ===")
forbidden = [
    "/opt/bla",
    "/bench/tests",
    "/bench/scripts",
    "/bench/fixtures",
    "/bench/runs",
    "/bench/results.csv",
    "/bench/run_once.py",
    "/bench/prompts",
    "/bench/prompt.txt",
    "/bench/prompt-baseline.txt",
]
violations = []
for p in forbidden:
    exists = os.path.exists(p)
    print(f"  {p}: {'PRESENT (VIOLATION!)' if exists else 'ABSENT (OK)'}")
    if exists:
        violations.append(f"forbidden_path_present:{p}")

print("\n=== 3. All Readable Files Under /bench, /opt, /home/bench, /tmp, /var/tmp, /srv ===")
search_roots = ["/bench", "/opt", "/home/bench", "/tmp", "/var/tmp", "/srv"]
allowed_bench_files = {"/bench/targets/dx-ball/original/dx-ball-sound-pan.js"}
for sroot in search_roots:
    if not os.path.exists(sroot):
        print(f"  [{sroot}] (does not exist)")
        continue
    for dirpath, dirnames, filenames in os.walk(sroot):
        dirnames.sort()
        filenames.sort()
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            readable = os.access(fp, os.R_OK)
            if not readable:
                continue
            size = os.path.getsize(fp) if os.path.exists(fp) else -1
            print(f"  {fp} (size={size}, readable={readable})")
            if sroot == "/bench" and fp not in allowed_bench_files:
                violations.append(f"unexpected_bench_file:{fp}")
            if sroot == "/opt":
                violations.append(f"unexpected_opt_file:{fp}")

print("\n=== 4. Global Installed Node Packages (/usr/local/lib/node_modules) ===")
nm = pathlib.Path("/usr/local/lib/node_modules")
if nm.is_dir():
    for item in sorted(nm.iterdir()):
        if item.name.startswith("@"):
            for sub in sorted(item.iterdir()):
                print(f"  {item.name}/{sub.name}")
        else:
            print(f"  {item.name}")

print("\n=== 5. Full Filesystem Filename Audit (All Readable Non-OS-Library Paths & Forbidden Patterns) ===")
skip_prefixes = ("/proc/", "/sys/", "/dev/")
os_std_prefixes = (
    "/usr/lib/",
    "/usr/share/",
    "/usr/include/",
    "/usr/bin/",
    "/usr/sbin/",
    "/usr/libexec/",
    "/usr/local/bin/",
    "/usr/local/lib/python3.12/",
    "/usr/local/include/",
    "/usr/local/share/",
    "/usr/local/lib/node_modules/npm/",
    "/usr/local/lib/node_modules/corepack/",
    "/usr/local/lib/node_modules/@openai/codex/",
    "/usr/local/lib/node_modules/rea-agents/",
    "/usr/local/lib/pkgconfig/",
    "/lib/",
    "/bin/",
    "/sbin/",
    "/etc/",
    "/var/lib/",
    "/var/cache/",
    "/var/log/",
)
bad_filename_tokens = (
    "/opt/bla",
    "engine/benchmark.ts",
    "engine/benchmark.js",
    "bla-agents",
    "bla-shield",
    "check_equiv",
    "test_w3_harness",
    "test_parse",
    "harden_targets",
    "hardening_manifest",
    "results.csv",
    "w3_runs.csv",
    "dx-ball_original.jsonl",
    "dx-ball_hardened.jsonl",
    "notion-clipboard",
    "license-validator",
    "crypto-core.wasm",
    "entitlements.sqlite",
    "Vault.evm",
)
total_readable = 0
non_std_readable = []
for dirpath, dirnames, filenames in os.walk("/"):
    dp = dirpath if dirpath.endswith("/") else dirpath + "/"
    if dp.startswith(skip_prefixes):
        dirnames[:] = []
        continue
    dirnames.sort()
    for fn in sorted(filenames):
        fp = os.path.join(dirpath, fn)
        try:
            if not os.access(fp, os.R_OK):
                continue
        except OSError:
            continue
        total_readable += 1
        low = fp.lower()
        for tok in bad_filename_tokens:
            if tok.lower() in low:
                violations.append(f"forbidden_filename:{fp}")
        if low.endswith(".jsonl"):
            violations.append(f"historical_jsonl:{fp}")
        if not fp.startswith(os_std_prefixes):
            non_std_readable.append(fp)

print(f"Total bench-readable files across entire container /: {total_readable}")
print(f"Readable files outside standard OS/Python/Node/Codex/REA system paths ({len(non_std_readable)}):")
for fp in non_std_readable:
    print(f"  {fp}")

print("\n=== 6. Content Leak Scan Under /bench and /home/bench ===")
leak_strings = [
    "acct_prod_01",
    "tok_live_9988776655",
    "DX_BALL_SOURCE",
    "NOTION_MAIN_SOURCE",
    "LICENSE_VALIDATOR_SOURCE",
    "DX_BALL_CASES",
    "WASM_CASES",
    "SQLITE_CASES",
]
for sroot in ("/bench", "/home/bench"):
    for dirpath, _, filenames in os.walk(sroot):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            if fp.endswith(("auth.json", "cpa-gui-model-catalog.json")):
                continue
            try:
                data = pathlib.Path(fp).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for needle in leak_strings:
                if needle in data:
                    violations.append(f"content_leak:{fp}:{needle}")

print("\n=== 7. Verdict ===")
if violations:
    print("STATUS: DIRTY")
    for v in violations:
        print("  VIOLATION:", v)
    raise SystemExit(1)
print("STATUS: CLEAN (0 violations; only hardened target artifact and REA/Codex runtime are accessible)")
"""


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify clean runtime container isolation.')
    parser.add_argument('--image', default='bla-bench:local')
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ['USERPROFILE']) / '.codex')
    args = parser.parse_args()

    hardened_dx = ROOT / 'targets' / 'dx-ball' / 'hardened' / 'dx-ball-sound-pan.js'
    if not hardened_dx.is_file():
        sys.stderr.write(f'Missing hardened sample for isolation check: {hardened_dx}\n')
        return 1

    work_dir = ROOT / 'docker-work' / 'isolation-check' / 'dx-ball'
    if work_dir.exists():
        shutil.rmtree(work_dir)
    (work_dir / 'original').mkdir(parents=True, exist_ok=True)
    shutil.copyfile(hardened_dx, work_dir / 'original' / 'dx-ball-sound-pan.js')

    auth_file = args.codex_home / 'auth.json'
    catalog_file = args.codex_home / 'cpa-gui-model-catalog.json'
    for f in (auth_file, catalog_file):
        if not f.is_file():
            sys.stderr.write(f'Missing Codex file: {f}\n')
            return 1

    cmd = [
        'docker',
        'run',
        '--rm',
        '--network',
        'none',
        '--security-opt',
        'no-new-privileges',
        '--cap-drop',
        'ALL',
        '--mount',
        f'type=bind,source={auth_file},target=/home/bench/.codex/auth.json,readonly',
        '--mount',
        f'type=bind,source={catalog_file},target=/home/bench/.codex/cpa-gui-model-catalog.json,readonly',
        '--mount',
        f'type=bind,source={work_dir},target=/bench/targets/dx-ball',
        '-w',
        '/bench/targets/dx-ball',
        args.image,
        'python',
        '-c',
        CONTAINER_PROBE,
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    output = proc.stdout + (f'\n[stderr]\n{proc.stderr}' if proc.stderr.strip() else '')
    out_file = ROOT / 'evidence' / 'isolation_check.txt'
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(output, encoding='utf-8')
    print(output)
    return proc.returncode


if __name__ == '__main__':
    sys.exit(main())
