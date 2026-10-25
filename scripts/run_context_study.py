#!/usr/bin/env python3
"""Run a saved synthetic context study; no model, network or live runtime.

The plan owns its complete fixture snapshot. Reports use the current canonical
engine, not an engine snapshot. The input file is always preserved, including
when it is already the output directory's plan.json.
"""
import argparse
import importlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = ROOT / 'experiments' / 'companion-input'
sys.path.insert(0, str(ROOT))
from context_lab.artifacts import paths_alias, write_reports


def output_paths(input_path, output_dir):
    targets = {name: output_dir / name for name in ('plan.json', 'result.json', 'result.md')}
    for name in ('result.json', 'result.md'):
        if paths_alias(input_path, targets[name]):
            raise ValueError('input aliases output ' + name + '; refusing to overwrite the input')
    values = list(targets.values())
    for index, target in enumerate(values):
        for other in values[index + 1:]:
            if paths_alias(target, other):
                raise ValueError('output paths alias each other: %s and %s' % (target.name, other.name))
        # A plan alias is deliberately retained byte-for-byte. Other symlinks
        # are rejected so writing a report cannot follow them elsewhere.
        if paths_alias(input_path, target):
            continue
        if target.is_symlink():
            raise ValueError('output path is a symbolic link: ' + str(target))
        if target.exists() and not target.is_file():
            raise ValueError('output path is not a regular file: ' + str(target))
    return targets


def reject_json_constant(value):
    raise ValueError('invalid JSON numeric constant: ' + value)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path, help='saved cc-context-study/1 JSON plan')
    parser.add_argument('--out', type=Path, default=ROOT / '.cache' / 'context-study',
                        help='local report directory (default: .cache/context-study)')
    args = parser.parse_args(argv)
    try:
        targets = output_paths(args.plan, args.out)
        raw = json.loads(args.plan.read_text(encoding='utf-8'), parse_constant=reject_json_constant)
        if str(ENGINE_DIR) not in sys.path:
            sys.path.insert(0, str(ENGINE_DIR))
        study = importlib.import_module('context_study')
        plan = study.validate_plan(raw)
        report = study.run_study(plan)
        # Finish all validation, projection and serialization before creating
        # the output directory or touching any existing report.
        markdown = study.render_markdown(report)
        serialized_plan = json.dumps(report['plan'], ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        serialized_report = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        if not isinstance(markdown, str):
            raise TypeError('render_markdown did not return text')
        contents = [(targets['result.json'], serialized_report), (targets['result.md'], markdown)]
        if not paths_alias(args.plan, targets['plan.json']):
            contents.insert(0, (targets['plan.json'], serialized_plan))
        write_reports(contents, args.out)
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        print('%s: error: %s' % (parser.prog, exc), file=sys.stderr)
        return 2
    print(json.dumps({'status': 'complete', 'schema': report['schema'],
                      'output': str(args.out), 'input_preserved': True}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
