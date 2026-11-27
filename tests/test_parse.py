import csv
import tempfile
import unittest
from pathlib import Path

from run_once import CSV_FIELDS, assess_run, parse_log, parse_usage, write_result


class ParseUsageTest(unittest.TestCase):
    def test_sums_only_completed_turns(self):
        jsonl = b'''{"type":"turn.started","usage":{"input_tokens":999}}
{"type":"turn.completed","usage":{"input_tokens":120,"cached_input_tokens":32,"output_tokens":17}}
{"type":"item.completed","usage":{"output_tokens":999}}
{"type":"turn.completed","usage":{"input_tokens":75,"cached_input_tokens":10,"output_tokens":8}}
{"type":"turn.completed"
'''
        totals, completed = parse_usage(jsonl.splitlines())
        self.assertEqual(completed, 2)
        self.assertEqual(totals, {'input_tokens': 195, 'cached_input_tokens': 42, 'output_tokens': 25})

    def test_no_usage_is_distinct_from_reported_zero(self):
        self.assertEqual(parse_usage(['{"type":"turn.failed"}'])[1], 0)
        self.assertEqual(parse_usage(['{"type":"turn.completed","usage":{"input_tokens":0}}'])[1], 1)

    def test_valid_run_counts_unique_calls_and_keeps_answer_separate(self):
        jsonl = '''{"type":"item.started","item":{"id":"item_1","type":"mcp_tool_call","status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_1","type":"mcp_tool_call","status":"completed"}}
{"type":"item.completed","item":{"id":"item_2","type":"mcp_tool_call","status":"failed","error":{"message":"Not a supported file format"}}}
'''
        _, _, calls = parse_log(jsonl.splitlines())
        self.assertEqual(assess_run(calls, 0, False, True), (True, '', 2, 1, True))
        self.assertEqual(assess_run(calls, 0, False, False), (True, '', 2, 1, False))

    def test_invalid_mcp_failures_even_with_zero_exit_code(self):
        jsonl = '''{"type":"item.started","item":{"id":"item_1","type":"mcp_tool_call","status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_1","type":"mcp_tool_call","server":"rea","tool":"open_binary","status":"failed","error":{"message":"MCP tool call requires approval, but approval policy is never"}}}
{"type":"item.completed","item":{"id":"item_2","type":"mcp_tool_call","server":"node_repl","tool":"js","status":"failed","result":{"content":[{"type":"text","text":"app runtime provisioning service is unavailable"}]}}}
{"type":"item.completed","item":{"id":"item_3","type":"command_execution","status":"failed"}}
'''
        _, _, calls = parse_log(jsonl.splitlines())
        valid, reason, total, failed, answers = assess_run(calls, 0, False, False)
        self.assertEqual((valid, total, failed, answers), (False, 2, 2, False))
        self.assertIn('rea.open_binary: MCP tool call requires approval', reason)
        self.assertIn('node_repl.js: app runtime provisioning service is unavailable', reason)

    def test_invalid_nonzero_exit_or_timeout(self):
        self.assertEqual(assess_run({}, 7, False, False), (False, 'Codex exit code 7', 0, 0, False))
        self.assertEqual(assess_run({}, 0, True, False), (False, 'timed out', 0, 0, False))

    def test_appends_rows_without_duplicate_header(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            result = Path(directory) / 'results.csv'
            row = ['value'] * len(CSV_FIELDS)
            write_result(result, row)
            write_result(result, row)
            with result.open(newline='', encoding='utf-8') as stream:
                self.assertEqual(list(csv.reader(stream)), [list(CSV_FIELDS), row, row])


if __name__ == '__main__':
    unittest.main()
