"""One local entry point; delegate to canonical scripts without new engines."""
import argparse
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = {
    'workbench': 'build_context_atlas.py',
    'case': 'run_context_case.py',
    'inspect': 'inspect_context.py',
    'import-run': 'import_cc_run.py',
    'study': 'run_context_study.py',
    'check': 'check_offline.py',
}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=[*COMMANDS, 'recipes'], help='existing offline workflow or recipe list')
    if not args or args[0] in ('-h', '--help'):
        parser.print_help()
        return 0
    command = parser.parse_args(args[:1]).command
    if command == 'recipes':
        if args[1:]:
            parser.error('recipes takes no arguments')
        from .recipes import load_catalog
        for recipe in load_catalog()['recipes']:
            print(recipe['id'] + '\t' + recipe['title'])
        return 0
    script = ROOT / 'scripts' / COMMANDS[command]
    original = sys.argv
    try:
        sys.argv = [str(script), *args[1:]]
        sys.path.insert(0, str(script.parent))
        runpy.run_path(str(script), run_name='__main__')
    finally:
        sys.argv = original
        sys.path.remove(str(script.parent))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
