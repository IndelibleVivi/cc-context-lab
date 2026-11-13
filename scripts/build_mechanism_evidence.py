#!/usr/bin/env python3
"""Project recipe evidence to stdout or the generated Handbook index, offline."""
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from context_lab.artifacts import write_reports
from context_lab.mechanisms import build_recipe_evidence
from context_lab.recipes import RECIPE_IDS, load_catalog

HANDBOOK_PATH = ROOT / 'docs/handbook/mechanism-evidence.md'


def render_handbook_evidence():
    """Reuse canonical claims and renderings; only rebase document navigation."""
    sections = [
        '# 机制与证据索引\n',
        '> 本页由 `python3 scripts/build_mechanism_evidence.py --write-handbook` '
        '生成；修改 canonical catalog 或 renderer 后重建，不手改表格。\n',
        '这份索引覆盖当前三条 recipe 使用的机制。claim IDs 连接具体判断与固定来源，'
        '相关阅读继续由 [Handbook](index.md) 和各专题拥有。它不是完整 CC 机制百科、'
        '真实 trace、跨阶段 receipt 或升级兼容性判定。来源版本与观察日期各自保留；'
        '固定一个历史 revision 不代表今天重新运行了那个 runtime。\n',
        'Workbench 的「逐条判断与固定来源」和下载复用同一份 Python projection。'
        '可以在仓库根目录运行 `python3 -m context_lab evidence --recipe owned-core '
        '--format json` 查看对应 canonical 数据；将 `json` 换为 `markdown` 查看报告。\n',
    ]
    bundles = [(recipe, build_recipe_evidence(recipe)) for recipe in load_catalog()['recipes']]
    sections.extend([
        '## 当前绑定一览\n',
        '| Recipe | Mechanism ID | Claim IDs | Evidence levels |',
        '| --- | --- | --- | --- |',
    ])
    for recipe, evidence in bundles:
        for mechanism in evidence['projection']['mechanisms']:
            claims = ', '.join('`' + claim['id'] + '`' for claim in mechanism['claims'])
            levels = ', '.join('`' + level + '`' for level in dict.fromkeys(claim['level'] for claim in mechanism['claims']))
            sections.append('| `' + recipe['id'] + '` | `' + mechanism['id'] + '` | ' + claims + ' | ' + levels + ' |')
    sections.append('')
    for recipe, evidence in bundles:
        # The renderer's links are rooted at the checkout for standalone use.
        # This tracked page lives two levels below it; evidence values stay exact.
        markdown = re.sub(
            r'\]\(((?:references|docs|context_lab|scripts|experiments)/[^)]+)\)',
            r'](../../\1)', evidence['markdown'])
        body, separator, raw_projection = markdown.partition('\n## Canonical projection\n')
        if not separator:
            raise ValueError('canonical evidence renderer omitted its projection section')
        markdown = body + '\n\n<details>\n<summary>完整 canonical JSON 与序列化边界</summary>\n\n' + raw_projection.rstrip() + '\n\n</details>\n'
        markdown = re.sub(r'^(#{1,5}) ', r'#\1 ', markdown, flags=re.MULTILINE)
        sections.extend(['---\n', markdown.rstrip() + '\n'])
    return '\n'.join(sections)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--recipe', choices=RECIPE_IDS, help='print one fixed recipe evidence projection')
    mode.add_argument('--check', action='store_true', help='reject a stale generated Handbook index')
    mode.add_argument('--write-handbook', action='store_true', help='rebuild the public authored-source projection')
    parser.add_argument('--format', choices=('json', 'markdown'), default='markdown')
    args = parser.parse_args(argv)
    if not args.recipe and args.format != 'markdown':
        parser.error('--format json requires --recipe')
    try:
        if args.recipe:
            recipe = next(r for r in load_catalog()['recipes'] if r['id'] == args.recipe)
            evidence = build_recipe_evidence(recipe)
            sys.stdout.write(evidence['json' if args.format == 'json' else 'markdown'])
            return 0
        rendered = render_handbook_evidence()
        if args.check:
            if not HANDBOOK_PATH.is_file() or HANDBOOK_PATH.read_text(encoding='utf-8') != rendered:
                print('Handbook evidence index is stale; run python3 scripts/build_mechanism_evidence.py --write-handbook', file=sys.stderr)
                return 1
            print('Handbook evidence index matches canonical recipe evidence.')
        elif args.write_handbook:
            write_reports([(HANDBOOK_PATH, rendered)], HANDBOOK_PATH.parent)
            print('Generated docs/handbook/mechanism-evidence.md')
        else:
            sys.stdout.write(rendered)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
