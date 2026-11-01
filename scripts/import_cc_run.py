#!/usr/bin/env python3
"""Import an explicitly selected local Claude Code run; never acquire one.

The selection manifest is the sole source inventory. This command has no log
discovery, transport, provider, native binary or transcript mutation path.
Both source bytes and generated evidence can be private.
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from context_lab.cc_runs import import_run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--selection', required=True, type=Path,
        help='explicit cc-source-selection/1 or /2 manifest')
    parser.add_argument(
        '--out', required=True, type=Path,
        help='private output directory outside Git or Git-ignored inside it')
    args = parser.parse_args(argv)
    try:
        run, _targets = import_run(ROOT, args.selection, args.out)
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print(f'{parser.prog}: error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps({
        'status': 'imported',
        'schema': run['schema'],
        'run_id': run['run_id'],
        'request_artifacts': len(run['attempts']),
        'responses': len(run['responses']),
        'events': len(run['events']),
        'output': str(args.out),
        'native_format_verified': False,
        'model_behavior': 'not_assessed',
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
