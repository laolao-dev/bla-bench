"""W3 全量容器实测编排脚本：5 样本 × original/hardened × 3 次 = 30 次交替运行。

严格遵守铁律：
1. 全部在隔离容器（--network bla-internal，Internal=true + bla-relay）内运行，每次重建干净工作区。
2. 追踪累计 input_tokens，超过 20,000,000 立即停止并保留已完成数据供出部分报告。
3. 单次超过 900 秒记为超时（run_once.py exit 124），绝不重试。
"""

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.inspect_run import inspect_jsonl

IMAGE = 'bla-bench:local'
NETWORK = 'bla-internal'
TOKEN_BUDGET_CAP = 20_000_000

SAMPLES = [
    ('dx-ball', 'dx-ball-sound-pan.js', 'prompt.txt'),
    ('notion-electron', 'notion-clipboard.asar', 'prompts/notion-electron.txt'),
    ('license-guard', 'license-validator.js', 'prompt.txt'),
    ('wasm-core', 'crypto-core.wasm', 'prompt.txt'),
    ('sqlite-db', 'entitlements.sqlite', 'prompts/sqlite-db.txt'),
]

W3_FIELDS = (
    'run_index',
    'round',
    'sample',
    'label',
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
)

MATCH_RE = re.compile(r'(\d+/\d+)\s+match')
JSONL_RE = re.compile(r'^JSONL:\s*(.+)$', re.MULTILINE)


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


def current_session_input_tokens(min_date: str = '2026-11-26') -> int:
    csv_path = ROOT / 'results.csv'
    if not csv_path.is_file():
        return 0
    total = 0
    with csv_path.open(encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            if row.get('env') == 'docker' and row.get('时间', '')[:10] >= min_date:
                val = row.get('input_tokens', '').strip()
                if val.isdigit():
                    total += int(val)
    return total


def load_completed_keys(w3_csv: Path) -> set[tuple[int, str, str]]:
    if not w3_csv.is_file():
        return set()
    done = set()
    with w3_csv.open(encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            done.add((int(row['round']), row['sample'], row['label']))
    return done


def append_w3_row(w3_csv: Path, row: dict) -> None:
    exists = w3_csv.is_file() and w3_csv.stat().st_size > 0
    with w3_csv.open('a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=W3_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def prepare_clean_target(sample: str, label: str, filename: str) -> Path:
    src = ROOT / 'targets' / sample / label / filename
    if not src.is_file():
        raise FileNotFoundError(f'Missing prepared artifact: {src}')
    work_dir = ROOT / 'docker-work' / 'targets' / sample
    if work_dir.exists():
        shutil.rmtree(work_dir)
    orig_slot = work_dir / 'original'
    orig_slot.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, orig_slot / filename)
    return work_dir


def read_last_results_row() -> dict:
    with (ROOT / 'results.csv').open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError('results.csv has no rows')
    return rows[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description='Run W3 30-run alternating container benchmark.')
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--budget', type=int, default=TOKEN_BUDGET_CAP)
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ['USERPROFILE']) / '.codex')
    args = parser.parse_args()

    auth_file = args.codex_home / 'auth.json'
    catalog_file = args.codex_home / 'cpa-gui-model-catalog.json'
    for cred in (auth_file, catalog_file):
        if not cred.is_file():
            raise FileNotFoundError(f'Missing required Codex file: {cred}')

    w3_csv = ROOT / 'evidence' / 'w3_runs.csv'
    answers_archive = ROOT / 'evidence' / 'w3-answers'
    answers_archive.mkdir(parents=True, exist_ok=True)
    completed = load_completed_keys(w3_csv)

    schedule: list[tuple[int, int, str, str, str, str]] = []
    idx = 0
    for rnd in range(1, args.rounds + 1):
        for sample, filename, prompt_rel in SAMPLES:
            for label in ('original', 'hardened'):
                idx += 1
                schedule.append((idx, rnd, sample, label, filename, prompt_rel))

    run_ps_stage('relay-start')
    try:
        verify_internal_network()
        for run_idx, rnd, sample, label, filename, prompt_rel in schedule:
            if (rnd, sample, label) in completed:
                print(f'[{run_idx:02d}/{len(schedule)}] SKIP completed r{rnd} {sample} {label}', flush=True)
                continue

            cum_tokens = current_session_input_tokens()
            if cum_tokens > args.budget:
                print(
                    f'BUDGET STOP: cumulative input tokens {cum_tokens:,} > {args.budget:,}; stopping cleanly.',
                    flush=True,
                )
                break

            verify_internal_network()
            work_target = prepare_clean_target(sample, label, filename)
            common = ['docker', 'run', '--rm', '--security-opt', 'no-new-privileges', '--cap-drop', 'ALL']
            mounts = [
                '--mount',
                f'type=bind,source={auth_file},target=/home/bench/.codex/auth.json,readonly',
                '--mount',
                f'type=bind,source={catalog_file},target=/home/bench/.codex/cpa-gui-model-catalog.json,readonly',
                '--mount',
                f'type=bind,source={ROOT / "results.csv"},target=/bench/results.csv',
                '--mount',
                f'type=bind,source={ROOT / "runs"},target=/bench/runs',
                '--mount',
                f'type=bind,source={work_target},target=/bench/targets/{sample}',
            ]
            cmd = [
                *common,
                '--network',
                NETWORK,
                *mounts,
                IMAGE,
                'run-sample',
                sample,
                label,
                prompt_rel,
            ]
            print(f'[{run_idx:02d}/{len(schedule)}] START r{rnd} {sample} ({label}) ...', flush=True)
            proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
            combined_out = (proc.stdout or '') + '\n' + (proc.stderr or '')
            m_jsonl = JSONL_RE.search(combined_out)
            if not m_jsonl:
                raise RuntimeError(f'run_once did not report JSONL path (rc={proc.returncode}):\n{combined_out}')
            jsonl_name = Path(m_jsonl.group(1).strip()).name
            jsonl_host = ROOT / 'runs' / jsonl_name
            inspected = inspect_jsonl(jsonl_host)
            last_csv = read_last_results_row()

            # 归档本次生成的 answer.py / answer.md
            ans_dir = answers_archive / f'{run_idx:02d}_r{rnd}_{sample}_{label}'
            if ans_dir.exists():
                shutil.rmtree(ans_dir)
            ans_dir.mkdir(parents=True, exist_ok=True)
            for ans_name in ('answer.py', 'answer.md'):
                candidate = work_target / ans_name
                if candidate.is_file():
                    shutil.copyfile(candidate, ans_dir / ans_name)

            # 在完全断网容器（--network none）内用真实未加固原件做正确性检查
            ref_fixture = ROOT / 'fixtures' / sample / filename
            eq_cmd = [
                *common,
                '--network',
                'none',
                '--mount',
                f'type=bind,source={work_target},target=/bench/targets/{sample},readonly',
                '--mount',
                f'type=bind,source={ref_fixture},target=/bench/ref-original/{filename},readonly',
                IMAGE,
                'equiv-sample',
                sample,
                f'/bench/ref-original/{filename}',
            ]
            eq_proc = subprocess.run(eq_cmd, check=False, capture_output=True, text=True)
            eq_text = (eq_proc.stdout or '') + '\n' + (eq_proc.stderr or '')
            m_score = MATCH_RE.search(eq_text)
            equiv_score = m_score.group(1) if m_score else '0/12'
            equiv_passed = eq_proc.returncode == 0

            in_tok = int(last_csv['input_tokens']) if last_csv['input_tokens'].isdigit() else 0
            cached_tok = int(last_csv['cached_input_tokens']) if last_csv['cached_input_tokens'].isdigit() else 0
            out_tok = int(last_csv['output_tokens']) if last_csv['output_tokens'].isdigit() else 0

            w3_row = {
                'run_index': run_idx,
                'round': rnd,
                'sample': sample,
                'label': label,
                'started_at': last_csv['时间'],
                'input_tokens': in_tok,
                'cached_input_tokens': cached_tok,
                'output_tokens': out_tok,
                'elapsed_sec': last_csv['秒数'],
                'exit_code': last_csv['退出码'],
                'timed_out': last_csv['是否超时'],
                'valid': last_csv['valid'],
                'invalid_reason': last_csv['invalid_reason'],
                'rea_calls': inspected['rea_calls'],
                'rea_failed': inspected['rea_failed'],
                'commands': inspected['commands'],
                'read_source_directly': inspected['read_source_directly'],
                'escaped_target_dir': inspected['escaped_target_dir'],
                'answer_exists': last_csv['answer_exists'],
                'equiv_passed': equiv_passed,
                'equiv_score': equiv_score,
                'jsonl_name': jsonl_name,
            }
            append_w3_row(w3_csv, w3_row)

            new_cum = current_session_input_tokens()
            print(
                f'[{run_idx:02d}/{len(schedule)}] DONE  r{rnd} {sample} ({label}): '
                f'in={in_tok:,} out={out_tok:,} t={last_csv["秒数"]}s '
                f'rea={inspected["rea_calls"]}(fail={inspected["rea_failed"]}) '
                f'read_src={inspected["read_source_directly"]} equiv={equiv_score}({"PASS" if equiv_passed else "FAIL"}) '
                f'cum_in={new_cum:,}',
                flush=True,
            )
            if new_cum > args.budget:
                print(
                    f'BUDGET STOP: cumulative input tokens {new_cum:,} > {args.budget:,}; stopping after run #{run_idx}.',
                    flush=True,
                )
                break
    finally:
        run_ps_stage('relay-stop')

    return 0


if __name__ == '__main__':
    sys.exit(main())
