#!/usr/bin/env python3
"""Inspect explicit local JSON request captures; no transport or runtime execution.

Raw bodies and generated reports may contain private data. The default output
is ignored local cache; keep real captures and their reports out of Git.
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from context_lab.artifacts import paths_alias, write_reports
from context_lab.observations import compare_observations, parse_capture_json, normalize_capture, render_markdown


def output_paths(inputs, output_dir, comparison):
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError('output directory is not a directory: ' + str(output_dir))
    targets = [output_dir / ('comparison.json' if comparison else 'observation.json'), output_dir / 'report.md']
    for target in targets:
        for incoming in inputs:
            if paths_alias(incoming, target):
                raise ValueError('input aliases output; refusing to overwrite input: ' + str(target))
        if target.is_symlink():
            raise ValueError('output is a symbolic link: ' + str(target))
        if target.exists() and not target.is_file():
            raise ValueError('output is not a regular file: ' + str(target))
    if paths_alias(*targets):
        raise ValueError('output paths alias each other')
    return targets


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path, help='harness-context-capture/1 JSON file')
    parser.add_argument('--compare', type=Path, help='candidate capture to compare with the baseline')
    parser.add_argument('--out', type=Path, default=ROOT / '.cache' / 'request-observation')
    args = parser.parse_args(argv)
    try:
        inputs = [args.capture] + ([args.compare] if args.compare else [])
        targets = output_paths(inputs, args.out, bool(args.compare))
        for path in inputs:
            if not path.is_file():
                raise ValueError('input is not a regular file: ' + str(path))
        observations = [normalize_capture(parse_capture_json(path.read_text(encoding='utf-8'))) for path in inputs]
        report = compare_observations(*observations) if args.compare else observations[0]
        # No output path is touched until validation, rendering and serialization finish.
        markdown = render_markdown(report)
        serialized = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        # An escaped lone surrogate is legal to Python's JSON decoder but
        # cannot be written as UTF-8; reject it before creating any output.
        serialized.encode('utf-8')
        markdown.encode('utf-8')
        write_reports(list(zip(targets, (serialized, markdown))), args.out)
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print(f'{parser.prog}: error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps({'status': 'complete', 'schema': report['schema'], 'output': str(args.out),
                      'input_preserved': True}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
