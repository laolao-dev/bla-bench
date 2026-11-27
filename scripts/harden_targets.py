"""在容器内调用 BLA 官方 CLI 生成 5 个入选样本的 hardened 版本并输出可验证清单。

锁定参数：
- BLA 仓库与提交：qybaihe/bla @ 8dcf9858f5c931e26c4d3526b29c8e10a97ec17f (bla-agents 3.6.0)
- 命令：node /opt/bla/dist/cli.js defend <input> -o <output> --intensity bankrupt --seed bla-benchmark-showcase-v1 --json
"""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

BLA_COMMIT = '8dcf9858f5c931e26c4d3526b29c8e10a97ec17f'
BLA_INTENSITY = 'bankrupt'
BLA_SEED = 'bla-benchmark-showcase-v1'

SELECTED_SAMPLES = [
    ('dx-ball', 'dx-ball-sound-pan.js'),
    ('notion-electron', 'notion-clipboard.asar'),
    ('license-guard', 'license-validator.js'),
    ('wasm-core', 'crypto-core.wasm'),
    ('sqlite-db', 'entitlements.sqlite'),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    fixtures_root = Path(sys.argv[1]).resolve()
    targets_root = Path(sys.argv[2]).resolve()
    manifest_out = Path(sys.argv[3]).resolve()
    bla_dir = Path('/opt/bla')

    head = subprocess.run(
        ['git', '-C', str(bla_dir), 'rev-parse', 'HEAD'],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if head != BLA_COMMIT:
        raise RuntimeError(f'BLA commit mismatch: expected {BLA_COMMIT}, got {head}')

    pkg_version = json.loads((bla_dir / 'package.json').read_text(encoding='utf-8'))['version']

    # 读取 BLA 官方 benchmark 报告中的估算倍数（同一 seed）
    bench_code = (
        "import('./dist/engine/benchmark.js').then(m => m.runShowcaseBenchmark({seed: "
        f"{json.dumps(BLA_SEED)}"
        '})).then(r => console.log(JSON.stringify(r)))'
    )
    bench_run = subprocess.run(
        ['node', '--input-type=module', '-e', bench_code],
        cwd=bla_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    bench_report = json.loads(bench_run.stdout)
    bench_by_id = {case['id']: case for case in bench_report['cases']}

    entries = []
    for sample_id, filename in SELECTED_SAMPLES:
        src = fixtures_root / sample_id / filename
        if not src.is_file():
            raise FileNotFoundError(f'Missing fixture: {src}')

        orig_dir = targets_root / sample_id / 'original'
        hard_dir = targets_root / sample_id / 'hardened'
        orig_dir.mkdir(parents=True, exist_ok=True)
        hard_dir.mkdir(parents=True, exist_ok=True)

        orig_dst = orig_dir / filename
        if not orig_dst.exists() or sha256_file(orig_dst) != sha256_file(src):
            shutil.copyfile(src, orig_dst)

        hard_dst = hard_dir / filename
        if hard_dst.exists():
            hard_dst.unlink()

        cmd = [
            'node',
            str(bla_dir / 'dist' / 'cli.js'),
            'defend',
            str(src),
            '-o',
            str(hard_dst),
            '--intensity',
            BLA_INTENSITY,
            '--seed',
            BLA_SEED,
            '--fail-under',
            '0',
            '--json',
        ]
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            sys.stderr.write(f'BLA defend failed for {sample_id}:\n{proc.stderr}\n{proc.stdout}\n')
            return 1

        report = json.loads(proc.stdout)
        if not report.get('overallSuccess'):
            sys.stderr.write(f'BLA defend overallSuccess=false for {sample_id}\n')
            return 1

        showcase = bench_by_id[sample_id]
        entries.append(
            {
                'id': sample_id,
                'filename': filename,
                'detected_format': report['protection']['detectedFormat'],
                'original_bytes': src.stat().st_size,
                'original_sha256': sha256_file(src),
                'hardened_bytes': hard_dst.stat().st_size,
                'hardened_sha256': sha256_file(hard_dst),
                'size_ratio': round(hard_dst.stat().st_size / src.stat().st_size, 2),
                'defense_score': report['verification']['defenseScore'],
                'rea_budgets_tripped': report['exhaustionSummary']['reaBudgetsTripped'],
                'bla_defend_modeled_token_multiplier': report['exhaustionSummary']['tokenAmplificationFactor'],
                'bla_benchmark_modeled_before_tokens': showcase['before']['estimatedTokens'],
                'bla_benchmark_modeled_after_tokens': showcase['after']['estimatedTokens'],
                'bla_benchmark_modeled_token_multiplier': showcase['tokenMultiplier'],
            }
        )
        print(
            f"{sample_id}: {src.stat().st_size} B -> {hard_dst.stat().st_size} B "
            f"(modeled {showcase['tokenMultiplier']}x)"
        )

    manifest = {
        'bla_repo': 'https://github.com/qybaihe/bla',
        'bla_version': pkg_version,
        'bla_commit': head,
        'cli_subcommand': 'defend',
        'intensity': BLA_INTENSITY,
        'seed': BLA_SEED,
        'command_template': (
            f'node /opt/bla/dist/cli.js defend <input> -o <output> --intensity {BLA_INTENSITY} --seed {BLA_SEED} --json'
        ),
        'bla_showcase_aggregate_modeled_token_multiplier': bench_report['aggregateTokenMultiplier'],
        'samples': entries,
    }
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
