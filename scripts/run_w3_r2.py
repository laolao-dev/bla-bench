"""W3 第二轮（纯净隔离运行容器）重跑脚本：只重跑 15 次 hardened（5 样本 × 3 次），原版 15 次沿用。

隔离保证：
- 运行镜像使用 bla-bench:local（runtime 阶段：无 /opt/bla、无 tests/scripts/fixtures）。
- 不挂载 /bench/runs、不挂载 /bench/results.csv；宿主机在容器外直接收集 stdout/stderr 写入 runs/。
- 运行容器内工作目录仅含 /bench/targets/<sample>/original/<加固产物>。
- 等价性检查在运行结束后由独立的断网容器 bla-bench:verifier（--network none）执行。
"""

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from run_once import REA_APPROVAL, TOKEN_FIELDS, assess_run, parse_log, write_result
from scripts.inspect_run import inspect_jsonl

RUNTIME_IMAGE = 'bla-bench:local'
VERIFIER_IMAGE = 'bla-bench:verifier'
NETWORK = 'bla-internal'
TOKEN_BUDGET_CAP = 20_000_000

SAMPLES = [
    ('dx-ball', 'dx-ball-sound-pan.js', 'prompt.txt'),
    ('notion-electron', 'notion-clipboard.asar', 'prompts/notion-electron.txt'),
    ('license-guard', 'license-validator.js', 'prompt.txt'),
    ('wasm-core', 'crypto-core.wasm', 'prompt.txt'),
    ('sqlite-db', 'entitlements.sqlite', 'prompts/sqlite-db.txt'),
]

W3_R2_FIELDS = (
    'run_index',
    'round',
    'sample',
    'label',
    'source_round',
    'started_at',
    'input_tokens',
    'cached_input_tokens',
    'output_tokens',
    'elapsed_sec',
    'exit_code',
    'timed_out',
    'valid',
    'invalid_reason',
    'rea_calls',
    'rea_failed',
    'commands',
    'read_source_directly',
    'escaped_target_dir',
    'answer_exists',
    'equiv_passed',
    'equiv_score',
    'jsonl_name',
    'defense_score',
    'bla_gate_note',
)

MATCH_RE = re.compile(r'(\d+/\d+)\s+match')


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def run_ps_stage(stage: str) -> None:
    ps_script = ROOT / 'run-docker.ps1'
    subprocess.run(
        ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ps_script), '-Stage', stage],
        cwd=ROOT,
        check=True,
    )


def verify_internal_network() -> None:
    out = subprocess.run(
        ['docker', 'network', 'inspect', '-f', '{{.Internal}}', NETWORK],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if out != 'true':
        raise RuntimeError(f'Docker network {NETWORK} is not --internal (got {out!r})')


def prepare_clean_target(sample: str, label: str, filename: str, expected_sha256: str | None = None) -> Path:
    if sample == 'baseline':
        src = ROOT / 'targets' / 'baseline' / 'original' / 'PLACEHOLDER.txt'
        filename = 'PLACEHOLDER.txt'
    else:
        src = ROOT / 'targets' / sample / label / filename
    if not src.is_file():
        raise FileNotFoundError(f'Missing prepared artifact: {src}')
    if expected_sha256 is not None and sha256_file(src) != expected_sha256:
        raise RuntimeError(f'SHA-256 mismatch on {src}: expected {expected_sha256}')
    work_dir = ROOT / 'docker-work' / 'targets' / sample
    if work_dir.exists():
        shutil.rmtree(work_dir)
    orig_slot = work_dir / 'original'
    orig_slot.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, orig_slot / filename)
    return work_dir


def run_clean_container_once(
    sample: str,
    label: str,
    work_target: Path,
    prompt_text: str,
    timeout_sec: int,
    codex_home: Path,
) -> tuple[str, dict]:
    auth_file = codex_home / 'auth.json'
    catalog_file = codex_home / 'cpa-gui-model-catalog.json'
    runs_dir = ROOT / 'runs'
    runs_dir.mkdir(exist_ok=True)

    started_at = datetime.now(UTC)
    timestamp = started_at.strftime('%Y%m%dT%H%M%S%f%z')
    raw_path = runs_dir / f'{timestamp}_{sample}_{label}.jsonl'
    stderr_path = raw_path.with_suffix('.stderr.txt')
    container_name = f'bla-run-{sample}-{started_at.strftime("%H%M%S%f")}'

    cmd = [
        'docker',
        'run',
        '--rm',
        '--name',
        container_name,
        '--security-opt',
        'no-new-privileges',
        '--cap-drop',
        'ALL',
        '--network',
        NETWORK,
        '--mount',
        f'type=bind,source={auth_file},target=/home/bench/.codex/auth.json,readonly',
        '--mount',
        f'type=bind,source={catalog_file},target=/home/bench/.codex/cpa-gui-model-catalog.json,readonly',
        '--mount',
        f'type=bind,source={work_target},target=/bench/targets/{sample}',
        '-w',
        f'/bench/targets/{sample}',
        RUNTIME_IMAGE,
        'codex',
        'exec',
        '--json',
        '--skip-git-repo-check',
        '-s',
        'danger-full-access',
        '-c',
        REA_APPROVAL,
        prompt_text,
    ]

    timed_out = False
    exit_code = None
    with raw_path.open('xb') as stdout_f, stderr_path.open('xb') as stderr_f:
        t0 = monotonic()
        with subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=stdout_f, stderr=stderr_f) as proc:
            try:
                exit_code = proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                timed_out = True
                subprocess.run(['docker', 'rm', '-f', container_name], check=False, capture_output=True)
                proc.kill()
                exit_code = proc.wait()
        elapsed = monotonic() - t0

    with raw_path.open('rb') as stream:
        totals, completed, mcp_items = parse_log(stream)

    answer_exists = all(
        (work_target / name).is_file() and (work_target / name).stat().st_size > 0
        for name in ('answer.py', 'answer.md')
    )
    assessment = assess_run(mcp_items, exit_code, timed_out, answer_exists)
    valid, invalid_reason, mcp_calls, mcp_failed, _ = assessment

    csv_row = [
        started_at.isoformat(timespec='seconds'),
        sample,
        label,
        *(totals[field] if completed else '' for field in TOKEN_FIELDS),
        f'{elapsed:.3f}',
        exit_code,
        timed_out,
        *assessment,
        'docker',
    ]
    write_result(ROOT / 'results.csv', csv_row)

    return raw_path.name, {
        'started_at': started_at.isoformat(timespec='seconds'),
        'input_tokens': totals['input_tokens'] if completed else 0,
        'cached_input_tokens': totals['cached_input_tokens'] if completed else 0,
        'output_tokens': totals['output_tokens'] if completed else 0,
        'elapsed_sec': f'{elapsed:.3f}',
        'exit_code': exit_code,
        'timed_out': timed_out,
        'valid': valid,
        'invalid_reason': invalid_reason,
        'mcp_calls': mcp_calls,
        'mcp_failed': mcp_failed,
        'answer_exists': answer_exists,
        'completed': completed,
    }


def run_equiv_in_verifier(sample: str, filename: str, work_target: Path) -> tuple[bool, str]:
    ref_fixture = ROOT / 'fixtures' / sample / filename
    eq_cmd = [
        'docker',
        'run',
        '--rm',
        '--security-opt',
        'no-new-privileges',
        '--cap-drop',
        'ALL',
        '--network',
        'none',
        '--mount',
        f'type=bind,source={work_target},target=/bench/targets/{sample},readonly',
        '--mount',
        f'type=bind,source={ref_fixture},target=/bench/ref-original/{filename},readonly',
        VERIFIER_IMAGE,
        'equiv-sample',
        sample,
        f'/bench/ref-original/{filename}',
    ]
    eq_proc = subprocess.run(eq_cmd, check=False, capture_output=True, text=True)
    eq_text = (eq_proc.stdout or '') + '\n' + (eq_proc.stderr or '')
    m_score = MATCH_RE.search(eq_text)
    equiv_score = m_score.group(1) if m_score else '0/12'
    return eq_proc.returncode == 0, equiv_score


def load_r2_completed(r2_csv: Path) -> dict[tuple[int, str, str], dict]:
    if not r2_csv.is_file():
        return {}
    with r2_csv.open(encoding='utf-8', newline='') as f:
        return {(int(r['round']), r['sample'], r['label']): r for r in csv.DictReader(f)}


def save_r2_rows(r2_csv: Path, rows: list[dict]) -> None:
    rows_sorted = sorted(rows, key=lambda x: int(x['run_index']))
    with r2_csv.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=W3_R2_FIELDS)
        writer.writeheader()
        writer.writerows(rows_sorted)


def main() -> int:
    parser = argparse.ArgumentParser(description='Run clean isolated W3 Round-2 hardened benchmark.')
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ['USERPROFILE']) / '.codex')
    parser.add_argument('--budget', type=int, default=TOKEN_BUDGET_CAP)
    parser.add_argument('--single-sample', default=None)
    parser.add_argument('--single-label', choices=('original', 'hardened', 'baseline'), default=None)
    parser.add_argument('--prompt-file', default='prompt.txt')
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--no-manage-relay', action='store_true')
    args = parser.parse_args()

    # 单次模式（供 run-docker.ps1 -Stage baseline / dx-ball 复用）
    if args.single_sample is not None:
        label = args.single_label or 'original'
        fname = {s: fn for s, fn, _ in SAMPLES}.get(args.single_sample, 'PLACEHOLDER.txt')
        prompt_text = (ROOT / args.prompt_file).read_text(encoding='utf-8').removesuffix('\n')
        verify_internal_network()
        wdir = prepare_clean_target(args.single_sample, label, fname)
        jname, stats = run_clean_container_once(
            args.single_sample, label, wdir, prompt_text, args.timeout, args.codex_home
        )
        print(f'JSONL: runs/{jname}')
        if args.single_sample != 'baseline':
            ok, score = run_equiv_in_verifier(args.single_sample, fname, wdir)
            print(f'{score} match')
            if not ok:
                return 1
        return 0 if stats['valid'] and stats['completed'] else 1

    manifest = json.loads((ROOT / 'evidence' / 'hardening_manifest.json').read_text(encoding='utf-8'))
    manifest_by_id = {s['id']: s for s in manifest['samples']}

    # 读取第一轮的 15 次 original 结果沿用
    with (ROOT / 'evidence' / 'w3_runs.csv').open(encoding='utf-8', newline='') as f:
        r1_rows = list(csv.DictReader(f))
    r1_originals = {(int(r['round']), r['sample']): r for r in r1_rows if r['label'] == 'original'}
    if len(r1_originals) != 15:
        raise RuntimeError(f'Expected 15 original runs from Round 1, found {len(r1_originals)}')

    r2_csv = ROOT / 'evidence' / 'w3_r2_runs.csv'
    existing = load_r2_completed(r2_csv)
    merged_rows: dict[tuple[int, str, str], dict] = dict(existing)

    # 先把沿用的 15 次 original 放进 merged_rows
    for (rnd, sample), orig in r1_originals.items():
        key = (rnd, sample, 'original')
        if key not in merged_rows:
            row_copy = {k: orig[k] for k in W3_R2_FIELDS if k in orig}
            row_copy['source_round'] = 'r1-reused'
            merged_rows[key] = row_copy

    answers_archive = ROOT / 'evidence' / 'w3-r2-answers'
    answers_archive.mkdir(parents=True, exist_ok=True)

    if not args.no_manage_relay:
        run_ps_stage('relay-start')
    try:
        verify_internal_network()
        r2_cum_input = sum(int(v['input_tokens']) for v in merged_rows.values() if v.get('source_round') == 'r2-clean')
        step_no = 0
        for rnd in range(1, 4):
            for s_idx, (sample, filename, prompt_rel) in enumerate(SAMPLES):
                step_no += 1
                run_idx = (rnd - 1) * 10 + s_idx * 2 + 2
                key = (rnd, sample, 'hardened')
                if key in merged_rows and merged_rows[key].get('source_round') == 'r2-clean':
                    print(f'[{step_no:02d}/15] SKIP completed r{rnd} {sample} hardened', flush=True)
                    continue

                if r2_cum_input > args.budget:
                    print(f'BUDGET STOP: r2 input tokens {r2_cum_input:,} > {args.budget:,}', flush=True)
                    break

                verify_internal_network()
                meta = manifest_by_id[sample]
                work_target = prepare_clean_target(
                    sample, 'hardened', filename, expected_sha256=meta['hardened_sha256']
                )
                prompt_text = (ROOT / prompt_rel).read_text(encoding='utf-8').removesuffix('\n')

                print(f'[{step_no:02d}/15] START clean r{rnd} {sample} (hardened) ...', flush=True)
                jsonl_name, stats = run_clean_container_once(
                    sample, 'hardened', work_target, prompt_text, 900, args.codex_home
                )
                inspected = inspect_jsonl(ROOT / 'runs' / jsonl_name)

                ans_dir = answers_archive / f'{run_idx:02d}_r{rnd}_{sample}_hardened'
                if ans_dir.exists():
                    shutil.rmtree(ans_dir)
                ans_dir.mkdir(parents=True, exist_ok=True)
                for ans_name in ('answer.py', 'answer.md'):
                    cand = work_target / ans_name
                    if cand.is_file():
                        shutil.copyfile(cand, ans_dir / ans_name)

                equiv_passed, equiv_score = run_equiv_in_verifier(sample, filename, work_target)
                score = int(meta['defense_score'])
                gate_note = '加固评分未达 BLA 默认门槛 (68/100 < 70)' if score < 70 else '达标'

                new_row = {
                    'run_index': run_idx,
                    'round': rnd,
                    'sample': sample,
                    'label': 'hardened',
                    'source_round': 'r2-clean',
                    'started_at': stats['started_at'],
                    'input_tokens': stats['input_tokens'],
                    'cached_input_tokens': stats['cached_input_tokens'],
                    'output_tokens': stats['output_tokens'],
                    'elapsed_sec': stats['elapsed_sec'],
                    'exit_code': stats['exit_code'],
                    'timed_out': stats['timed_out'],
                    'valid': stats['valid'],
                    'invalid_reason': stats['invalid_reason'],
                    'rea_calls': inspected['rea_calls'],
                    'rea_failed': inspected['rea_failed'],
                    'commands': inspected['commands'],
                    'read_source_directly': inspected['read_source_directly'],
                    'escaped_target_dir': inspected['escaped_target_dir'],
                    'answer_exists': stats['answer_exists'],
                    'equiv_passed': equiv_passed,
                    'equiv_score': equiv_score,
                    'jsonl_name': jsonl_name,
                    'defense_score': score,
                    'bla_gate_note': gate_note,
                }
                merged_rows[key] = new_row
                save_r2_rows(r2_csv, list(merged_rows.values()))
                r2_cum_input += int(stats['input_tokens'])

                print(
                    f'[{step_no:02d}/15] DONE  clean r{rnd} {sample} (hardened): '
                    f'in={stats["input_tokens"]:,} out={stats["output_tokens"]:,} t={stats["elapsed_sec"]}s '
                    f'rea={inspected["rea_calls"]}(fail={inspected["rea_failed"]}) '
                    f'escape={inspected["escaped_target_dir"]} '
                    f'equiv={equiv_score}({"PASS" if equiv_passed else "FAIL"}) '
                    f'r2_cum_in={r2_cum_input:,}',
                    flush=True,
                )
    finally:
        if not args.no_manage_relay:
            run_ps_stage('relay-stop')

    return 0


if __name__ == '__main__':
    sys.exit(main())
