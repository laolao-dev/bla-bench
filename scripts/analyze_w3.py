"""统计分析 W3 第一轮与第二轮（纯净运行容器重跑）实测数据，输出两轮对比、JSONL 直接解析证据与对比图。"""

import csv
import json
import re
import sys
from pathlib import Path
from statistics import median

SAMPLE_ORDER = ['dx-ball', 'notion-electron', 'license-guard', 'wasm-core', 'sqlite-db']
BLA_DEFAULT_MIN_DEFENSE_SCORE = 70
BELOW_GATE_NOTE = '加固评分未达 BLA 默认门槛'

DIRECT_PARSE_CMD_RE = re.compile(r'original(?:/|\\)|\.rea-|\.ipc-')
WRITES_ANSWER_RE = re.compile(r'Begin Patch|answer\.(?:py|md)')


def compute_multiplier(orig_inputs: list[int], hard_inputs: list[int], baseline_tokens: float) -> dict:
    if not orig_inputs or not hard_inputs:
        raise ValueError('Both original and hardened token lists must be non-empty')
    orig_med = float(median(orig_inputs))
    hard_med = float(median(hard_inputs))
    net_orig = orig_med - baseline_tokens
    net_hard = hard_med - baseline_tokens
    if net_orig <= 0:
        raise ValueError(f'Non-positive net original tokens: {net_orig}')
    return {
        'orig_median_input': orig_med,
        'hard_median_input': hard_med,
        'orig_net_input': net_orig,
        'hard_net_input': net_hard,
        'multiplier': round(net_hard / net_orig, 2),
    }


def compute_interception_rate(hardened_equiv_passed: list[bool]) -> dict:
    if not hardened_equiv_passed:
        raise ValueError('hardened_equiv_passed must be non-empty')
    intercepted = sum(1 for passed in hardened_equiv_passed if not passed)
    total = len(hardened_equiv_passed)
    return {
        'intercepted': intercepted,
        'total': total,
        'rate': round(intercepted / total, 4),
    }


def summarize_group(sample_ids: list[str], per_sample: dict) -> dict:
    present = [s for s in sample_ids if s in per_sample]
    mults = [per_sample[s]['multiplier'] for s in present]
    intercepted = sum(per_sample[s]['interception']['intercepted'] for s in present)
    total_hard = sum(per_sample[s]['interception']['total'] for s in present)
    orig_ok = sum(per_sample[s]['orig_pass_count'] for s in present)
    total_orig = sum(per_sample[s]['orig_runs'] for s in present)
    return {
        'sample_ids': present,
        'sample_count': len(present),
        'multipliers': {s: per_sample[s]['multiplier'] for s in present},
        'median_multiplier': round(float(median(mults)), 2) if mults else None,
        'min_multiplier': min(mults) if mults else None,
        'max_multiplier': max(mults) if mults else None,
        'original_pass': f'{orig_ok}/{total_orig}',
        'interception': {
            'intercepted': intercepted,
            'total': total_hard,
            'rate': round(intercepted / total_hard, 4) if total_hard else None,
        },
    }


def extract_direct_parse_evidence(runs_dir: Path, jsonl_name: str) -> dict:
    path = runs_dir / jsonl_name
    rea_fail_line = None
    rea_fail_tool = None
    direct_cmd_line = None
    direct_cmd_snippet = None
    if not path.is_file():
        return {}
    with path.open(encoding='utf-8') as f:
        for line_no, raw in enumerate(f, 1):
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if ev.get('type') != 'item.completed':
                continue
            item = ev.get('item') or {}
            if item.get('type') == 'mcp_tool_call' and item.get('server') == 'rea' and item.get('status') == 'failed':
                if rea_fail_line is None:
                    rea_fail_line = line_no
                    rea_fail_tool = f"rea.{item.get('tool')}"
            elif item.get('type') == 'command_execution':
                cmd = item.get('command') or ''
                # 排除开局仅做 ls -la 的目录查看命令，提取真正直接读取/解析产物的命令
                is_trivial_ls = cmd.strip() in (
                    "/bin/bash -lc 'ls -la; ls -la original'",
                    '/bin/bash -lc "ls -la; ls -la original"',
                ) or (
                    'ls -la original' in cmd
                    and 'python' not in cmd
                    and 'node' not in cmd
                    and 'head' not in cmd
                    and 'sed' not in cmd
                    and 'sqlite3' not in cmd
                )
                if (
                    direct_cmd_line is None
                    and not is_trivial_ls
                    and DIRECT_PARSE_CMD_RE.search(cmd)
                    and not WRITES_ANSWER_RE.search(cmd)
                ):
                    direct_cmd_line = line_no
                    direct_cmd_snippet = cmd.replace('\n', ' ')[:150]
    return {
        'jsonl_name': jsonl_name,
        'rea_failed_line': rea_fail_line,
        'rea_failed_tool': rea_fail_tool,
        'direct_parse_line': direct_cmd_line,
        'direct_parse_snippet': direct_cmd_snippet,
    }


def analyze_single_suite(
    suite_csv: Path,
    baseline_med: float,
    w2_baselines: list[int],
    manifest_by_id: dict,
    runs_dir: Path,
) -> dict:
    with suite_csv.open(encoding='utf-8', newline='') as f:
        w3_rows = list(csv.DictReader(f))

    per_sample = {}
    for sample in SAMPLE_ORDER:
        s_rows = [r for r in w3_rows if r['sample'] == sample]
        orig_rows = [r for r in s_rows if r['label'] == 'original']
        hard_rows = [r for r in s_rows if r['label'] == 'hardened']
        if not orig_rows or not hard_rows:
            continue
        orig_in = [int(r['input_tokens']) for r in orig_rows]
        hard_in = [int(r['input_tokens']) for r in hard_rows]
        orig_sec = [float(r['elapsed_sec']) for r in orig_rows]
        hard_sec = [float(r['elapsed_sec']) for r in hard_rows]
        orig_pass = [r['equiv_passed'] == 'True' for r in orig_rows]
        hard_pass = [r['equiv_passed'] == 'True' for r in hard_rows]

        mult_info = compute_multiplier(orig_in, hard_in, baseline_med)
        inter_info = compute_interception_rate(hard_pass)
        meta = manifest_by_id[sample]
        score = int(meta['defense_score'])
        meets_gate = score >= BLA_DEFAULT_MIN_DEFENSE_SCORE
        evidences = [extract_direct_parse_evidence(runs_dir, r['jsonl_name']) for r in hard_rows]
        per_sample[sample] = {
            **mult_info,
            'defense_score': score,
            'meets_bla_default_gate': meets_gate,
            'bla_gate_note': '达标'
            if meets_gate
            else f'{BELOW_GATE_NOTE} ({score}/100 < {BLA_DEFAULT_MIN_DEFENSE_SCORE})',
            'orig_runs': len(orig_rows),
            'hard_runs': len(hard_rows),
            'orig_inputs': orig_in,
            'hard_inputs': hard_in,
            'orig_median_sec': round(float(median(orig_sec)), 2),
            'hard_median_sec': round(float(median(hard_sec)), 2),
            'orig_pass_count': sum(orig_pass),
            'hard_pass_count': sum(hard_pass),
            'interception': inter_info,
            'orig_read_src_count': sum(1 for r in orig_rows if r['read_source_directly'] == 'True'),
            'hard_read_src_count': sum(1 for r in hard_rows if r['read_source_directly'] == 'True'),
            'hard_escape_count': sum(1 for r in hard_rows if r.get('escaped_target_dir') == 'True'),
            'hard_timeouts': sum(1 for r in hard_rows if r['timed_out'] == 'True'),
            'bla_modeled_multiplier': meta['bla_benchmark_modeled_token_multiplier'],
            'original_bytes': meta['original_bytes'],
            'hardened_bytes': meta['hardened_bytes'],
            'hardened_evidence': evidences,
        }

    gate_passed_ids = [s for s in SAMPLE_ORDER if s in per_sample and per_sample[s]['meets_bla_default_gate']]
    all_ids = [s for s in SAMPLE_ORDER if s in per_sample]
    gate_passed_group = summarize_group(gate_passed_ids, per_sample)
    all_samples_group = summarize_group(all_ids, per_sample)
    hard_only_input = sum(int(r['input_tokens']) for r in w3_rows if r['label'] == 'hardened')
    hard_only_output = sum(int(r['output_tokens']) for r in w3_rows if r['label'] == 'hardened')

    return {
        'baseline_runs': w2_baselines[:3],
        'baseline_median_input_tokens': int(baseline_med),
        'bla_default_min_defense_score': BLA_DEFAULT_MIN_DEFENSE_SCORE,
        'total_w3_runs': len(w3_rows),
        'total_w3_input_tokens': sum(int(r['input_tokens']) for r in w3_rows),
        'total_w3_output_tokens': sum(int(r['output_tokens']) for r in w3_rows),
        'hardened_15_input_tokens': hard_only_input,
        'hardened_15_output_tokens': hard_only_output,
        'groups': {
            'gate_passed': gate_passed_group,
            'all_samples': all_samples_group,
        },
        'median_of_sample_multipliers': all_samples_group['median_multiplier'],
        'original_pass_rate': all_samples_group['original_pass'],
        'overall_interception': all_samples_group['interception'],
        'samples': per_sample,
    }


def build_comparison(r1: dict, r2: dict) -> dict:
    per_sample_diff = {}
    for s in SAMPLE_ORDER:
        if s not in r1['samples'] or s not in r2['samples']:
            continue
        m1 = r1['samples'][s]['multiplier']
        m2 = r2['samples'][s]['multiplier']
        delta = round(m2 - m1, 2)
        rel_pct = round((m2 - m1) / m1 * 100.0, 1)
        per_sample_diff[s] = {
            'r1_hard_median_input': r1['samples'][s]['hard_median_input'],
            'r2_hard_median_input': r2['samples'][s]['hard_median_input'],
            'r1_multiplier': m1,
            'r2_multiplier': m2,
            'abs_diff': delta,
            'rel_diff_pct': rel_pct,
            'r1_interception': f"{r1['samples'][s]['interception']['intercepted']}/{r1['samples'][s]['interception']['total']}",
            'r2_interception': f"{r2['samples'][s]['interception']['intercepted']}/{r2['samples'][s]['interception']['total']}",
        }
    return {
        'gate_passed_r1_median': r1['groups']['gate_passed']['median_multiplier'],
        'gate_passed_r2_median': r2['groups']['gate_passed']['median_multiplier'],
        'all_samples_r1_median': r1['groups']['all_samples']['median_multiplier'],
        'all_samples_r2_median': r2['groups']['all_samples']['median_multiplier'],
        'r1_interception': r1['overall_interception'],
        'r2_interception': r2['overall_interception'],
        'per_sample': per_sample_diff,
    }


def plot_summary(summary: dict, out_png: Path, out_svg: Path) -> None:
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import Patch

    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Meiryo', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    samples = [s for s in SAMPLE_ORDER if s in summary['samples']]
    xlabels = [s if summary['samples'][s]['meets_bla_default_gate'] else f'{s}*\n(68/100 < 70 gate)' for s in samples]
    measured = [max(summary['samples'][s]['multiplier'], 0.05) for s in samples]
    raw_measured = [summary['samples'][s]['multiplier'] for s in samples]
    modeled = [summary['samples'][s]['bla_modeled_multiplier'] for s in samples]
    meets_gate = [summary['samples'][s]['meets_bla_default_gate'] for s in samples]
    intercepts = [
        f"{summary['samples'][s]['interception']['intercepted']}/{summary['samples'][s]['interception']['total']}"
        for s in samples
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.2, 5.9), gridspec_kw={'width_ratios': [1.48, 1.0]})
    x = np.arange(len(samples))
    width = 0.36

    meas_colors = ['#2563eb' if ok else '#f59e0b' for ok in meets_gate]
    bars_meas = ax1.bar(x - width / 2, measured, width, color=meas_colors)
    bars_mod = ax1.bar(x + width / 2, modeled, width, color='#94a3b8')
    ax1.set_yscale('log')
    ax1.set_ylabel('Input Token Multiplier (log scale)')
    ax1.set_title('Clean R2 Measured vs. BLA Modeled Multiplier (n=3 median, baseline deducted)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(xlabels, fontsize=8.8)
    ax1.axhline(1.0, color='#dc2626', linestyle='--', linewidth=1.0)
    ax1.set_ylim(0.1, max(modeled) * 35.0)
    ax1.grid(axis='y', linestyle=':', alpha=0.5)
    ax1.legend(
        handles=[
            Patch(facecolor='#2563eb', label='Measured Multiplier — Clean R2 (Gate-Passing >=70)'),
            Patch(
                facecolor='#f59e0b',
                label='Measured Multiplier — Clean R2 (*Below Default Gate: 68/100, --fail-under 0)',
            ),
            Patch(facecolor='#94a3b8', label='BLA Modeled Estimate (REA-only static model)'),
        ],
        loc='upper left',
        fontsize=8.0,
    )

    for bar, val, ok in zip(bars_meas, raw_measured, meets_gate):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() * 1.15,
            f'{val:.2f}x',
            ha='center',
            va='bottom',
            fontsize=8.5,
            fontweight='bold',
            color='#1e3a8a' if ok else '#b45309',
        )
    for bar, val in zip(bars_mod, modeled):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() * 1.15,
            f'{val:.1f}x',
            ha='center',
            va='bottom',
            fontsize=7.8,
            color='#475569',
        )

    rates_pct = [summary['samples'][s]['interception']['rate'] * 100.0 for s in samples]
    int_colors = ['#0f766e' if ok else '#d97706' for ok in meets_gate]
    bars_int = ax2.bar(x, rates_pct, width=0.52, color=int_colors)
    ax2.set_ylim(0, 118)
    ax2.set_ylabel('Hardened Interception Rate (%)')
    g_pass = summary['groups']['gate_passed']['interception']
    g_all = summary['groups']['all_samples']['interception']
    ax2.set_title(
        f"Clean R2 Interception — Gate-Passing: {g_pass['intercepted']}/{g_pass['total']} ({g_pass['rate'] * 100:.1f}%) | "
        f"All: {g_all['intercepted']}/{g_all['total']} ({g_all['rate'] * 100:.1f}%)",
        fontsize=9.6,
    )
    ax2.set_xticks(x)
    ax2.set_xticklabels(xlabels, fontsize=8.8)
    ax2.grid(axis='y', linestyle=':', alpha=0.5)
    for bar, pct, frac, ok in zip(bars_int, rates_pct, intercepts, meets_gate):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            pct + 3.0,
            f'{frac}\n({pct:.0f}%)',
            ha='center',
            va='bottom',
            fontsize=8.5,
            fontweight='bold',
            color='#134e4a' if ok else '#92400e',
        )

    gp_med = summary['groups']['gate_passed']['median_multiplier']
    all_med = summary['groups']['all_samples']['median_multiplier']
    fig.suptitle(
        f"BLA v3.6.0 Clean Container Benchmark (Baseline = {summary['baseline_median_input_tokens']:,} tok | "
        f"Median Multiplier: Gate-Passing={gp_med}x, All={all_med}x)",
        fontsize=11.0,
        fontweight='bold',
    )
    fig.text(
        0.5,
        0.01,
        '* Note: sqlite-db scored 68/100 in default stock SQLite mode (below BLA default minDefenseScore=70 gate; '
        'emitted with --fail-under 0 / 加固评分未达 BLA 默认门槛).',
        ha='center',
        fontsize=8.3,
        color='#92400e',
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=180)
    fig.savefig(out_svg)
    plt.close(fig)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    with (root / 'results.csv').open(encoding='utf-8', newline='') as f:
        all_rows = list(csv.DictReader(f))
    w2_baselines = [
        int(r['input_tokens'])
        for r in all_rows
        if r['env'] == 'docker' and r['label'] == 'baseline' and r['时间'].startswith('2026-11-26')
    ]
    baseline_med = float(median(w2_baselines[:3]))

    manifest = json.loads((root / 'evidence' / 'hardening_manifest.json').read_text(encoding='utf-8'))
    manifest_by_id = {s['id']: s for s in manifest['samples']}
    runs_dir = root / 'runs'

    r1_summary = analyze_single_suite(
        root / 'evidence' / 'w3_runs.csv', baseline_med, w2_baselines, manifest_by_id, runs_dir
    )
    r2_csv = root / 'evidence' / 'w3_r2_runs.csv'
    r2_summary = analyze_single_suite(r2_csv, baseline_med, w2_baselines, manifest_by_id, runs_dir)
    comparison = build_comparison(r1_summary, r2_summary)

    combined = {
        **r2_summary,
        'active_round': 'round2_clean_isolated',
        'round1_summary': r1_summary,
        'round1_vs_round2': comparison,
    }
    (root / 'evidence' / 'w3_summary.json').write_text(
        json.dumps(combined, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    plot_summary(
        r2_summary,
        root / 'evidence' / 'w3_comparison.png',
        root / 'evidence' / 'w3_comparison.svg',
    )
    print(
        json.dumps(
            {'round2_groups': r2_summary['groups'], 'comparison': comparison, 'r2_samples': r2_summary['samples']},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
