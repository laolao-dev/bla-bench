import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parent
TOKEN_FIELDS = ('input_tokens', 'cached_input_tokens', 'output_tokens')
RUN_FIELDS = ('valid', 'invalid_reason', 'mcp_calls', 'mcp_failed', 'answer_exists')
CSV_FIELDS = ('时间', '样本', 'label', *TOKEN_FIELDS, '秒数', '退出码', '是否超时', *RUN_FIELDS, 'env')
RUN_ENV = os.environ.get('BLA_BENCH_ENV', 'host')
# 容器内 bwrap 无法建 user namespace，由容器充当沙箱；本机默认不变
SANDBOX_MODE = os.environ.get('BLA_CODEX_SANDBOX', 'workspace-write')
REA_APPROVAL = 'mcp_servers.rea.default_tools_approval_mode="approve"'
PROVISIONING_UNAVAILABLE = re.compile(
    r'\b(?:app runtime )?provisioning service is unavailable(?:; refusing helper fallback)?',
    re.IGNORECASE,
)
BLOCKED_MCP = re.compile(
    r'\b(?:requires? approval|approval (?:policy|denied|timed out|not granted)|'
    r'permission denied|access (?:is )?denied|unauthorized|forbidden|'
    r'provisioning[^\n]*unavailable|sandbox (?:failed|denied|unavailable)|'
    r'connection (?:closed|refused|reset)|handshak\w+[^\n]*failed|'
    r'kernel exited|server (?:startup failed|unavailable)|environment unavailable)\b',
    re.IGNORECASE,
)


def parse_usage(lines):
    totals, completed, _ = parse_log(lines)
    return totals, completed


def parse_log(lines):
    totals = dict.fromkeys(TOKEN_FIELDS, 0)
    completed = 0
    mcp_items = {}
    for index, line in enumerate(lines):
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get('type')
        if kind in ('item.started', 'item.updated', 'item.completed'):
            item = event.get('item')
            if isinstance(item, dict) and item.get('type') == 'mcp_tool_call':
                mcp_items[item.get('id', index)] = item
        if kind != 'turn.completed':
            continue
        usage = event.get('usage')
        if not isinstance(usage, dict):
            continue
        completed += 1
        for field in TOKEN_FIELDS:
            value = usage.get(field)
            if type(value) is int and value >= 0:
                totals[field] += value
    return totals, completed, mcp_items


def assess_run(mcp_items, exit_code, timed_out, answer_exists):
    reasons = []
    if timed_out:
        reasons.append('timed out')
    if exit_code is None:
        reasons.append('Codex exit code unavailable')
    elif exit_code != 0:
        reasons.append(f'Codex exit code {exit_code}')
    failed = 0
    for item in mcp_items.values():
        if item.get('status') != 'failed':
            continue
        failed += 1
        error = item.get('error')
        message = error.get('message') if isinstance(error, dict) else error
        result = item.get('result')
        content = result.get('content', []) if isinstance(result, dict) else []
        lines = [message] if isinstance(message, str) else []
        lines.extend(part['text'] for part in content if isinstance(part, dict) and isinstance(part.get('text'), str))
        for text in lines:
            provisioning = PROVISIONING_UNAVAILABLE.search(text)
            matched = (
                provisioning.group()
                if provisioning
                else next((line.strip() for line in text.splitlines() if BLOCKED_MCP.search(line)), None)
            )
            if matched:
                tool = f"{item.get('server', '?')}.{item.get('tool', '?')}"
                reasons.append(f'{tool}: {matched}')
                break
    return not reasons, '; '.join(reasons), len(mcp_items), failed, answer_exists


def answer_state(target):
    state = []
    for name in ('answer.py', 'answer.md'):
        path = target / name
        stat = path.stat() if not path.is_symlink() and path.is_file() else None
        state.append((stat.st_size, stat.st_mtime_ns) if stat is not None else None)
    return state


def write_result(path, row):
    with path.open('a+', newline='', encoding='utf-8') as stream:
        stream.seek(0)
        header = next(csv.reader(stream), None)
        if header is not None and header != list(CSV_FIELDS):
            raise ValueError(f'Unexpected results.csv schema: {header}')
        stream.seek(0, 2)
        writer = csv.writer(stream)
        if header is None:
            writer.writerow(CSV_FIELDS)
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description='Run Codex once and record reported token usage.')
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--label', choices=('original', 'hardened', 'baseline'), required=True)
    parser.add_argument('--prompt-file', type=Path, default=ROOT / 'prompt.txt')
    parser.add_argument('--timeout', type=int, default=900)
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error('--timeout must be a positive number of seconds')
    target = args.target.resolve()
    artifact_dir = (target / 'original').resolve()
    if (
        not target.is_relative_to(ROOT)
        or target == ROOT
        or not artifact_dir.is_relative_to(target)
        or not artifact_dir.is_dir()
        or not any(artifact_dir.iterdir())
    ):
        parser.error('--target must be a sample directory inside bla-bench with files in ./original')
    codex = shutil.which('codex.exe' if sys.platform == 'win32' else 'codex')
    if codex is None:
        parser.error('Codex executable was not found on PATH')

    prompt = args.prompt_file.read_text(encoding='utf-8').removesuffix('\n')
    started_at = datetime.now().astimezone()
    timestamp = started_at.strftime('%Y%m%dT%H%M%S%f%z')
    runs = ROOT / 'runs'
    runs.mkdir(exist_ok=True)
    raw_path = runs / f'{timestamp}_{target.name}_{args.label}.jsonl'
    stderr_path = raw_path.with_suffix('.stderr.txt')
    command = [codex, 'exec', '--json', '--skip-git-repo-check', '-s', SANDBOX_MODE, '-c', REA_APPROVAL, prompt]
    before_answers = answer_state(target)
    timed_out = False
    exit_code = None
    with raw_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
        start = monotonic()
        try:
            with subprocess.Popen(
                command, cwd=target, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr
            ) as process:
                try:
                    exit_code = process.wait(timeout=args.timeout)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    process.kill()
                    exit_code = process.wait()
        except OSError as error:
            stderr.write(f'{error}\n'.encode())
        elapsed = monotonic() - start

    with raw_path.open('rb') as stream:
        totals, completed, mcp_items = parse_log(stream)
    answer_exists = all(
        after is not None and after[0] > 0 and before != after
        for before, after in zip(before_answers, answer_state(target))
    )
    assessment = assess_run(mcp_items, exit_code, timed_out, answer_exists)
    valid, invalid_reason, *_ = assessment
    write_result(
        ROOT / 'results.csv',
        [
            started_at.isoformat(timespec='seconds'),
            target.name,
            args.label,
            *(totals[field] if completed else '' for field in TOKEN_FIELDS),
            f'{elapsed:.3f}',
            exit_code,
            timed_out,
            *assessment,
            RUN_ENV,
        ],
    )

    print(f'JSONL: {raw_path}\nStderr: {stderr_path}')
    if not completed:
        print('No completed-turn usage received; token fields were left blank.', file=sys.stderr)
    if not valid:
        print(f'Invalid run: {invalid_reason}', file=sys.stderr)
    if timed_out:
        return 124
    return 0 if valid and completed else 1


if __name__ == '__main__':
    sys.exit(main())
