#!/usr/bin/env python3
"""Synthetic Atlas output-boundary regressions; no Git, runtime or network calls."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('atlas_output_safety', ROOT / 'scripts/build_context_atlas.py')
atlas = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(atlas)


def synthetic_data():
    return {'model': {'capabilities': []}, 'upstreams': [], 'scenarios': [],
            'synthetic_capture': 'SYNTHETIC_PRIVATE_BODY'}


class AtlasOutputSafetyTests(unittest.TestCase):
    def run_main(self, output, captures=(), data=None, renderer=None, data_only=False):
        argv = ['build_context_atlas.py', '--out', str(output)]
        if data_only:
            argv.append('--data-only')
        for capture in captures:
            argv += ['--capture', str(capture)]
        kwargs = {'return_value': '<html>SYNTHETIC</html>'} if renderer is None else {'side_effect': renderer}
        with patch.object(sys, 'argv', argv), \
                patch.object(atlas, 'build_data', return_value=deepcopy(synthetic_data() if data is None else data)), \
                patch.object(atlas, 'compose_html', **kwargs), \
                patch.object(atlas.subprocess, 'run', side_effect=AssertionError('unexpected Git/process call')), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            try:
                result = atlas.main()
            except SystemExit as exc:
                return exc.code
        return 0 if result is None else result

    def test_symbolic_outputs_never_overwrite_victim_or_follow_dangling_link(self):
        for name in ('data.json', 'index.html'):
            for exists in (False, True):
                with self.subTest(target=name, victim_exists=exists), tempfile.TemporaryDirectory() as directory:
                    base = Path(directory)
                    out = base / 'out'
                    out.mkdir()
                    incoming = base / 'capture.json'
                    incoming.write_text('SYNTHETIC INPUT')
                    victim = base / 'victim'
                    if exists:
                        victim.write_text('KEEP VICTIM')
                    (out / name).symlink_to(victim)
                    self.assertEqual(self.run_main(out, [incoming]), 2)
                    self.assertEqual(victim.read_text() if exists else victim.exists(), 'KEEP VICTIM' if exists else False)
                    self.assertEqual(incoming.read_text(), 'SYNTHETIC INPUT')
                    self.assertEqual(sorted(p.name for p in out.iterdir()), [name])

    def test_hardlinked_unrelated_files_survive_successful_replacement(self):
        for name in ('data.json', 'index.html'):
            with self.subTest(target=name), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                out = base / 'out'
                out.mkdir()
                victim = base / 'victim'
                victim.write_text('KEEP VICTIM')
                os.link(victim, out / name)
                self.assertEqual(self.run_main(out), 0)
                self.assertEqual(victim.read_text(), 'KEEP VICTIM')
                self.assertFalse(os.path.samefile(victim, out / name))
                self.assertEqual(sorted(p.name for p in out.iterdir()), ['data.json', 'index.html'])

    def test_capture_input_aliases_are_rejected_for_both_targets(self):
        for name in ('data.json', 'index.html'):
            for alias in ('samepath', 'symlink', 'hardlink'):
                with self.subTest(target=name, alias=alias), tempfile.TemporaryDirectory() as directory:
                    base = Path(directory)
                    out = base / 'out'
                    out.mkdir()
                    incoming = out / name if alias == 'samepath' else base / 'capture.json'
                    incoming.write_text('KEEP INPUT')
                    if alias == 'symlink':
                        (out / name).symlink_to(incoming)
                    elif alias == 'hardlink':
                        os.link(incoming, out / name)
                    self.assertEqual(self.run_main(out, [incoming]), 2)
                    self.assertEqual(incoming.read_text(), 'KEEP INPUT')
                    self.assertEqual(sorted(p.name for p in out.iterdir()), [name])

    def test_mutually_aliased_outputs_and_nonregular_targets_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            (out / 'data.json').write_text('KEEP BOTH')
            os.link(out / 'data.json', out / 'index.html')
            self.assertEqual(self.run_main(out), 2)
            self.assertEqual((out / 'data.json').read_text(), 'KEEP BOTH')
            self.assertEqual((out / 'index.html').read_text(), 'KEEP BOTH')
        for name in ('data.json', 'index.html'):
            with self.subTest(target=name), tempfile.TemporaryDirectory() as directory:
                out = Path(directory)
                (out / name).mkdir()
                self.assertEqual(self.run_main(out), 2)
                self.assertEqual(sorted(p.name for p in out.iterdir()), [name])

    def test_surrogate_and_renderer_failure_preserve_previous_outputs(self):
        invalid = synthetic_data()
        invalid['surrogate'] = '\ud800'
        for failure in ('surrogate', 'renderer'):
            for existing in (False, True):
                with self.subTest(failure=failure, existing=existing), tempfile.TemporaryDirectory() as directory:
                    out = Path(directory) / 'out'
                    if existing:
                        out.mkdir()
                        (out / 'data.json').write_text('KEEP JSON')
                        (out / 'index.html').write_text('KEEP HTML')
                    kwargs = {'data': invalid} if failure == 'surrogate' else {'renderer': ValueError('SYNTHETIC RENDER FAILURE')}
                    self.assertEqual(self.run_main(out, **kwargs), 2)
                    if existing:
                        self.assertEqual((out / 'data.json').read_text(), 'KEEP JSON')
                        self.assertEqual((out / 'index.html').read_text(), 'KEEP HTML')
                        self.assertEqual(sorted(p.name for p in out.iterdir()), ['data.json', 'index.html'])
                    else:
                        self.assertFalse(out.exists())

    def test_capture_output_inside_worktree_requires_ignore_without_process_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            out = root / 'tracked-output'
            incoming = root / 'capture.json'
            incoming.write_text('SYNTHETIC INPUT')
            argv = ['build_context_atlas.py', '--capture', str(incoming), '--out', str(out)]
            with patch.object(atlas, 'ROOT', root), patch.object(sys, 'argv', argv), \
                    patch.object(atlas.subprocess, 'run') as check_ignore, \
                    patch.object(atlas, 'build_data') as build, \
                    redirect_stderr(io.StringIO()):
                check_ignore.return_value.returncode = 1
                with self.assertRaises(SystemExit) as caught:
                    atlas.main()
                self.assertEqual(caught.exception.code, 2)
                check_ignore.assert_called_once()
                self.assertEqual(check_ignore.call_args.args[0][:3], ['git', 'check-ignore', '--quiet'])
                build.assert_not_called()
            self.assertFalse(out.exists())
            self.assertEqual(incoming.read_text(), 'SYNTHETIC INPUT')

    def test_success_serializes_synthetic_data_without_changing_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            incoming = base / 'capture.json'
            incoming.write_text('SYNTHETIC INPUT')
            out = base / 'out'
            data = synthetic_data()
            data['exact_integer'] = 9007199254740993
            self.assertEqual(self.run_main(out, [incoming], data=data), 0)
            self.assertEqual(json.loads((out / 'data.json').read_text())['exact_integer'], 9007199254740993)
            self.assertEqual((out / 'index.html').read_text(), '<html>SYNTHETIC</html>')
            self.assertEqual(incoming.read_text(), 'SYNTHETIC INPUT')
            self.assertEqual(sorted(p.name for p in out.iterdir()), ['data.json', 'index.html'])

    def test_real_capture_projection_preserves_canonical_numbers_and_each_display_value(self):
        capture = {'schema': 'harness-context-capture/1', 'capture_id': 'A',
                   'evidence': {'kind': 'synthetic_fixture', 'observed_at': None},
                   'runtime': {'harness': 'synthetic'}, 'wire_format': 'openai-responses',
                   'body': {'instructions': '  SYNTHETIC\n\n尾行\n',
                            'input': [{'type': 'future_context_item', 'exact': 9007199254740993}],
                            'future_parameter': {'exact': 9007199254740993}}}
        candidate = deepcopy(capture)
        candidate['capture_id'] = 'B'
        candidate['body']['input'].append({'type': 'future_context_item', 'added': True})
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ('A.json', 'B.json')]
            for destination, value in zip(paths, (capture, candidate)):
                destination.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
            data = atlas.build_request_observations(paths)
        for aid, candidates in data['comparisons'].items():
            for bid, comparison in candidates.items():
                with self.subTest(baseline=aid, candidate=bid):
                    self.assertEqual(json.loads(data['json_reports'][aid][bid]), comparison)
                    self.assertIn('9007199254740993', data['json_reports'][aid][bid])
                    self.assertEqual(data['reports'][aid][bid], atlas.request_observation.render_markdown(comparison))
                    display = data['display_values'][aid][bid]
                    self.assertEqual(len(display['sections']), len(comparison['sections']))
                    for row, rendered in zip(comparison['sections'], display['sections']):
                        for side in ('baseline', 'candidate'):
                            expected = None if row[side] is None else row[side]['value']
                            if expected is None or isinstance(expected, str):
                                self.assertEqual(rendered[side], expected)
                            else:
                                self.assertEqual(json.loads(rendered[side]), expected)
                    for side in ('baseline', 'candidate'):
                        for destination, original in (('body', 'request_body'), ('parameters', 'request_parameters')):
                            text = display['bodies'][side][destination]
                            self.assertEqual(json.loads(text), comparison[side][original])
                            self.assertIn('9007199254740993', text)


if __name__ == '__main__':
    unittest.main()
