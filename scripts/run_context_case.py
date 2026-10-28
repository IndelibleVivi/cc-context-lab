#!/usr/bin/env python3
"""Run one self-contained context case; no tracing, model or network calls.

Case and report bodies may contain private data. Output must be outside the
Git worktree or in an ignored directory inside it. The only subprocess is a
read-only `git check-ignore` privacy check.
"""

import argparse
import importlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = ROOT / 'experiments' / 'companion-input'
sys.path.insert(0, str(ROOT))

from context_lab.artifacts import paths_alias, write_reports
from context_lab.case_demo import make_demo_case
from context_lab.cases import render_markdown, run_case
from context_lab.observations import parse_capture_json


def ensure_private_output(output_dir):
    """Require an external path or a Git-ignored worktree path."""
    try:
        relative = output_dir.resolve().relative_to(ROOT)
    except ValueError:
        return
    checked = subprocess.run(
        ['git', 'check-ignore', '--quiet', '--', str(relative)],
        cwd=ROOT, capture_output=True, text=True)
    if checked.returncode != 0:
        raise ValueError(
            'case output inside the worktree must be Git-ignored; '
            'use .cache/ or an external directory')


def output_paths(input_path, output_dir):
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError('output directory is not a directory: ' + str(output_dir))
    targets = {
        name: output_dir / name
        for name in ('case.json', 'report.json', 'report.md')
    }
    for name in ('report.json', 'report.md'):
        if input_path is not None and paths_alias(input_path, targets[name]):
            raise ValueError(
                'input aliases output ' + name +
                '; refusing to overwrite the input')
    values = list(targets.values())
    for index, target in enumerate(values):
        for other in values[index + 1:]:
            if paths_alias(target, other):
                raise ValueError(
                    'output paths alias each other: %s and %s'
                    % (target.name, other.name))
        if input_path is not None and paths_alias(input_path, target):
            continue
        if target.is_symlink():
            raise ValueError('output path is a symbolic link: ' + str(target))
        if target.exists() and not target.is_file():
            raise ValueError(
                'output path is not a regular file: ' + str(target))
    return targets


def _load_study_module():
    if str(ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_DIR))
    return importlib.import_module('context_study')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'case', nargs='?', type=Path,
        help='saved harness-context-case/1 JSON file')
    parser.add_argument(
        '--demo', action='store_true',
        help='build the authored synthetic demo from the canonical fixture')
    parser.add_argument(
        '--out', type=Path,
        default=ROOT / '.cache' / 'context-case',
        help='private output directory (default: .cache/context-case)')
    args = parser.parse_args(argv)
    if args.demo == (args.case is not None):
        parser.error('provide exactly one of case or --demo')
    try:
        ensure_private_output(args.out)
        targets = output_paths(args.case, args.out)
        if args.case is not None:
            if not args.case.is_file():
                raise ValueError(
                    'case is not a regular file: ' + str(args.case))
            manifest = parse_capture_json(
                args.case.read_text(encoding='utf-8'))
        else:
            fixture_path = (
                ENGINE_DIR / 'fixtures' / 'common_scenario.json')
            fixture = parse_capture_json(
                fixture_path.read_text(encoding='utf-8'))
            manifest = make_demo_case(fixture)

        study = _load_study_module()
        report = run_case(manifest, study_runner=study.run_study)

        # Finish every projection and encoding before creating the output
        # directory or replacing any prior report.
        markdown = render_markdown(report)
        if not isinstance(markdown, str):
            raise TypeError('render_markdown did not return text')
        serialized_case = (
            json.dumps(report['case'], ensure_ascii=False, indent=2,
                       allow_nan=False) + '\n')
        serialized_report = (
            json.dumps(report, ensure_ascii=False, indent=2,
                       allow_nan=False) + '\n')
        markdown.encode('utf-8')
        serialized_case.encode('utf-8')
        serialized_report.encode('utf-8')

        contents = [
            (targets['report.json'], serialized_report),
            (targets['report.md'], markdown),
        ]
        if args.case is None or not paths_alias(
                args.case, targets['case.json']):
            contents.insert(0, (targets['case.json'], serialized_case))
        write_reports(contents, args.out)
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print(f'{parser.prog}: error: {exc}', file=sys.stderr)
        return 2

    failed = report['summary']['failed']
    status = 'scoped_requirement_failure' if failed else 'complete'
    print(json.dumps({
        'status': status,
        'schema': report['schema'],
        'output': str(args.out),
        'input_preserved': True,
        'failed_requirements': failed,
        'readiness_claim': False,
    }, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
