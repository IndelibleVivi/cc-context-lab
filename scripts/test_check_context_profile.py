"""Process-level checks of exit semantics, fresh copies and environment isolation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name('check_context_profile.py')
FAKE = r'''
import json, os, pathlib, sys, time
case = CASE
assert 'ANTHROPIC_API_KEY' not in os.environ
assert 'CLAUDE_CODE_PLUGIN_DIRS' not in os.environ
assert pathlib.Path(os.environ['CLAUDE_CONFIG_DIR']).is_dir()
args = sys.argv[1:]
if args == ['--version']:
    if case == 'timeout': time.sleep(2)
    if case == 'version_error': sys.exit(1)
    print('2.1.289 (Claude Code)')
elif args[:2] == ['plugin', 'validate']:
    root = pathlib.Path(args[2])
    assert not (root / '.claude-plugin/types/stale.d.ts').exists()
    if case == 'unsupported':
        print("error: unknown command 'validate'", file=sys.stderr); sys.exit(1)
    if case == 'malformed':
        print('looks successful'); sys.exit(0)
    print(json.dumps({'success': case != 'invalid'}))
    sys.exit(1 if case == 'invalid' else 0)
elif args[:2] == ['plugin', 'test']:
    if case == 'disabled':
        print('claude plugin test: hooks modules are turned off here'); sys.exit(1)
    if case == 'failed':
        print('0 pass\n1 fail\nRan 1 test across 1 file.'); sys.exit(1)
    if case == 'empty':
        print('0 pass\n0 fail\nRan 0 tests across 0 files.'); sys.exit(0)
    if case == 'generated':
        p = pathlib.Path(args[2]) / '.claude-plugin/types/new.d.ts'
        p.parent.mkdir(); p.write_text('// synthetic generated output')
    print('3 pass\n0 fail\nRan 3 tests across 1 file.')
else: sys.exit(9)
'''


class CheckWorkflow(unittest.TestCase):
    def exercise(self, case, expected_code, expected_status):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'plugin'
            meta = source / '.claude-plugin'
            (meta / 'types').mkdir(parents=True)
            (meta / 'plugin.json').write_text('{"name":"synthetic"}')
            stale = meta / 'types/stale.d.ts'
            stale.write_text('// previous build')
            fake = root / 'claude'
            fake.write_text('#!' + sys.executable + '\n' + FAKE.replace('CASE', repr(case)))
            fake.chmod(0o755)
            env = dict(os.environ, ANTHROPIC_API_KEY='synthetic-secret', CLAUDE_CODE_PLUGIN_DIRS='synthetic-foreign-plugin')
            args = [sys.executable, str(CHECK), '--claude', str(fake), '--plugin', str(source), '--output', str(root / 'output')]
            if case == 'timeout': args += ['--timeout', '0.1']
            result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, expected_code, result.stderr + result.stdout)
            summary = json.loads(result.stdout)
            self.assertEqual(summary['offline_status'], expected_status)
            report = json.loads(Path(summary['report']).read_text())
            self.assertEqual(stale.read_text(), '// previous build')
            self.assertEqual(report['request_behavior'], 'not_tested')
            self.assertEqual(report['model_behavior'], 'not_tested')
            if case == 'generated':
                self.assertEqual(report['target_types']['status'], 'generated_not_reviewed')
            else:
                self.assertEqual(report['target_types']['status'], 'not_generated')
            if case in {'invalid', 'unsupported', 'malformed', 'timeout', 'version_error'}:
                self.assertNotIn('test', report['steps'])

    def test_real_process_statuses_and_input_boundaries(self):
        cases = [('passed', 0, 'passed'), ('generated', 0, 'passed'),
                 ('invalid', 1, 'failed'), ('failed', 1, 'failed'), ('empty', 1, 'failed'),
                 ('unsupported', 2, 'unsupported'), ('disabled', 2, 'unavailable'),
                 ('malformed', 2, 'unrecognized_output'), ('timeout', 2, 'unavailable'),
                 ('version_error', 2, 'unavailable')]
        for case, code, status in cases:
            with self.subTest(case=case): self.exercise(case, code, status)

    def test_missing_executable(self):
        result = subprocess.run([sys.executable, str(CHECK), '--claude', '/nonexistent/cc-context-lab-claude'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['reason'], 'executable_not_found')


if __name__ == '__main__': unittest.main()
