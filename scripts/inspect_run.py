"""汇总一次 codex exec --json 原始日志：token、REA 调用、是否直接读取 original/ 源码或越界访问。

用法: python scripts/inspect_run.py <run.jsonl>
"""

import json
import re
import sys
from pathlib import Path

SAMPLE_FILENAMES = (
    r'dx-ball-sound-pan\.js|notion-clipboard\.asar|license-validator\.js|'
    r'crypto-core\.wasm|entitlements\.sqlite'
)
READ_SOURCE = re.compile(rf'original(?:/|\\)|(?:{SAMPLE_FILENAMES})')
WRITES_ANSWER = re.compile(r'Begin Patch|answer\.(?:py|md)')
ESCAPE_TARGET = re.compile(r'(?:^|[\s"\'/\\])\.\.(?:/|\\)|/bench/(?:fixtures|targets|ref-original)|/opt/bla')


def inspect_jsonl(path: str | Path) -> dict:
    usage: dict[str, int] = {}
    mcp: dict[str, dict] = {}
    reads: list[str] = []
    escapes: list[str] = []
    commands = 0
    with open(path, encoding='utf-8') as stream:
        for idx, line in enumerate(stream):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            item = event.get('item') or {}
            if event.get('type') == 'turn.completed':
                for key, value in (event.get('usage') or {}).items():
                    if isinstance(value, int):
                        usage[key] = usage.get(key, 0) + value
            if event.get('type') != 'item.completed':
                continue
            if item.get('type') == 'mcp_tool_call':
                call_id = str(item.get('id', idx))
                mcp[call_id] = {
                    'server': item.get('server'),
                    'tool': item.get('tool'),
                    'status': item.get('status'),
                    'summary': f"{item.get('server')}.{item.get('tool')}:{item.get('status')}",
                }
            elif item.get('type') == 'command_execution':
                commands += 1
                command = item.get('command') or ''
                compact = command[:160].replace('\n', ' ')
                # 写 answer.* 的命令会在正文里引用源码路径，不算读取
                if READ_SOURCE.search(command) and not WRITES_ANSWER.search(command):
                    reads.append(compact)
                if ESCAPE_TARGET.search(command):
                    escapes.append(compact)
    rea_items = [v for v in mcp.values() if v['server'] == 'rea']
    rea_failed = sum(1 for v in rea_items if v['status'] == 'failed')
    return {
        'usage': usage,
        'mcp_calls': [v['summary'] for v in mcp.values()],
        'mcp_total': len(mcp),
        'mcp_failed': sum(1 for v in mcp.values() if v['status'] == 'failed'),
        'rea_calls': len(rea_items),
        'rea_failed': rea_failed,
        'commands': commands,
        'read_source_directly': bool(reads),
        'source_read_commands': reads,
        'escaped_target_dir': bool(escapes),
        'escape_commands': escapes,
    }


def main():
    report = inspect_jsonl(sys.argv[1])
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
