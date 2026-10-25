#!/usr/bin/env python3
"""Pure local synthetic contract and CLI checks; no provider/runtime calls."""

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from context_lab.observations import (compare_observations, parse_capture_json,
                                      normalize_capture, render_markdown)

FIXTURES = ROOT / 'experiments' / 'request-observation' / 'fixtures'
CLI = ROOT / 'scripts' / 'inspect_context.py'
spec = importlib.util.spec_from_file_location('inspect_context', CLI)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def fixture(name='anthropic-a'):
    return parse_capture_json((FIXTURES / (name + '.json')).read_text(encoding='utf-8'))


def observe(name='anthropic-a'):
    return normalize_capture(fixture(name))


class ObservationTests(unittest.TestCase):
    def test_all_fixtures_normalize_without_mutating_source(self):
        for path in sorted(FIXTURES.glob('*.json')):
            with self.subTest(path=path.name):
                capture = parse_capture_json(path.read_text(encoding='utf-8'))
                before = deepcopy(capture)
                result = normalize_capture(capture)
                self.assertEqual(capture, before)
                self.assertEqual(result['request_body'], capture['body'])
                self.assertEqual(result['runtime']['version'], 'synthetic')
                self.assertEqual(result['evidence']['kind'], 'synthetic_fixture')
                self.assertEqual(result['evidence']['provenance'], 'imported_manifest')
                self.assertEqual(result['evidence']['model_behavior'], 'NOT_ASSESSED')
                self.assertEqual(result['evidence']['external_delivery'], 'NOT_ASSESSED')

    def test_anthropic_fidelity_and_midstream_system(self):
        capture = fixture()
        result = normalize_capture(capture)
        self.assertEqual([s['pointer'] for s in result['sections']],
                         ['/system', '/messages/0', '/messages/1', '/messages/2', '/messages/3', '/tools/0'])
        values = {s['pointer']: s['value'] for s in result['sections']}
        self.assertEqual(values['/system'], capture['body']['system'])
        self.assertEqual(values['/tools/0'], capture['body']['tools'][0])
        self.assertEqual(values['/messages/0']['content'][1]['source']['data'], 'SYNTHETIC_BASE64_PLACEHOLDER')
        self.assertEqual(values['/messages/3'], capture['body']['messages'][3])
        self.assertEqual(result['sections'][3]['role'], 'system')
        self.assertEqual(result['sections'][3]['kind'], 'message')
        for section in result['sections']:
            self.assertEqual(set(section), {'id', 'pointer', 'kind', 'role', 'origin', 'lifecycle', 'value'})
            self.assertEqual(section['id'], section['pointer'])
            self.assertEqual(section['origin'], 'unknown')
            self.assertEqual(section['lifecycle'], 'unknown')
        result['request_body']['system'][0]['text'] = 'mutated'
        values['/tools/0']['input_schema']['required'].append('extra')
        self.assertNotEqual(result['request_body']['system'], values['/system'])
        self.assertEqual(capture, fixture())

    def test_responses_preserves_opaque_items_and_array_instructions(self):
        capture = fixture('responses-a')
        result = normalize_capture(capture)
        rows = {s['pointer']: s for s in result['sections']}
        self.assertEqual(rows['/instructions']['value'], capture['body']['instructions'])
        self.assertEqual(rows['/input/0']['kind'], 'message')
        for index in (1, 2, 3, 4):
            self.assertEqual(rows[f'/input/{index}']['kind'], 'opaque')
            self.assertEqual(rows[f'/input/{index}']['value'], capture['body']['input'][index])
        self.assertIsNone(rows['/input/2']['role'])
        self.assertEqual(result['request_parameters']['future_parameter'], capture['body']['future_parameter'])
        self.assertNotIn('instructions', result['request_parameters'])
        self.assertNotIn('tools', result['request_parameters'])

    def test_source_metadata_is_preserved_but_never_promoted(self):
        capture = fixture('responses-a')
        capture['evidence']['kind'] = 'captured_request'
        capture['evidence']['observed_at'] = '2026-10-25T08:00:00+08:00'
        capture['body']['input'][0]['origin'] = 'trusted-human'
        capture['body']['input'][0]['lifecycle'] = 'current'
        result = normalize_capture(capture)
        section = result['sections'][1]
        self.assertEqual(section['value']['origin'], 'trusted-human')
        self.assertEqual(section['origin'], 'unknown')
        self.assertEqual(section['lifecycle'], 'unknown')
        self.assertEqual(result['evidence']['provenance'], 'imported_manifest')
        self.assertEqual(result['evidence']['model_behavior'], 'NOT_ASSESSED')
        capture['evidence']['model_behavior'] = 'VERIFIED'
        with self.assertRaisesRegex(ValueError, 'evidence'):
            normalize_capture(capture)

    def test_previous_response_and_template_gaps_do_not_fabricate_history(self):
        capture = fixture('responses-b')
        del capture['body']['input']
        capture['body']['conversation'] = {'id': 'SYNTHETIC_CONVERSATION'}
        capture['body']['prompt'] = {'id': 'SYNTHETIC_TEMPLATE', 'variables': {'question': 'synthetic'}}
        result = normalize_capture(capture)
        self.assertEqual(len(result['unresolved_context']), 3)
        self.assertEqual([s['pointer'] for s in result['sections']], ['/instructions', '/tools/0'])
        self.assertNotIn('input', result['request_body'])
        self.assertIn('server-side/unexpanded', ' '.join(result['limitations']))
        self.assertEqual(result['request_parameters']['prompt'], capture['body']['prompt'])

    def test_each_explicit_state_reference_allows_absent_input(self):
        for key, value in [('previous_response_id', 'SYNTHETIC_RESPONSE'),
                           ('conversation', 'SYNTHETIC_CONVERSATION'),
                           ('prompt', {'id': 'SYNTHETIC_TEMPLATE'})]:
            with self.subTest(key=key):
                capture = fixture('responses-a')
                del capture['body']['input']
                capture['body'][key] = value
                result = normalize_capture(capture)
                self.assertEqual(len(result['unresolved_context']), 1)
                self.assertIn('/' + key, result['unresolved_context'][0])
                self.assertFalse(any(s['pointer'].startswith('/input') for s in result['sections']))

    def test_string_input_and_unknown_runtime_labels(self):
        capture = fixture('responses-a')
        capture['runtime'] = {'harness': 'synthetic-harness'}
        capture['body']['input'] = '  preserve\n\n尾行\n'
        result = normalize_capture(capture)
        self.assertEqual(result['sections'][1]['pointer'], '/input')
        self.assertEqual(result['sections'][1]['value'], capture['body']['input'])
        self.assertEqual(result['sections'][1]['role'], 'user')
        self.assertEqual(result['runtime']['version'], None)
        self.assertIn('真实人类', ' '.join(result['limitations']))

    def test_malformed_manifest_and_structural_shapes(self):
        cases = [
            ('schema', 'wrong', 'schema'), ('capture_id', '  ', 'capture_id'),
            ('wire_format', 'openai-chat', 'wire_format'), ('body', [], 'body'),
            ('runtime', {'harness': ''}, 'runtime/harness'),
            ('runtime', {'harness': 'synthetic', 'version': 1}, 'runtime/version'),
            ('evidence', {'kind': 'runtime_verified', 'observed_at': None}, 'evidence/kind'),
            ('evidence', {'kind': 'synthetic_fixture', 'observed_at': '2026-10-25'}, 'evidence/observed_at'),
            ('evidence', {'kind': 'synthetic_fixture'}, 'evidence/observed_at'),
        ]
        for key, value, error in cases:
            with self.subTest(key=key, value=value):
                capture = fixture()
                capture[key] = value
                with self.assertRaisesRegex(ValueError, error):
                    normalize_capture(capture)
        for field, value in [('system', {}), ('system', ['bad block']), ('messages', None),
                             ('messages', ['bad message']), ('messages', [{'role': 'user', 'content': 42}]),
                             ('messages', [{'role': 'user', 'content': ['bad block']}]),
                             ('tools', {}), ('tools', ['bad tool'])]:
            with self.subTest(field=field, value=value):
                capture = fixture()
                capture['body'][field] = value
                with self.assertRaisesRegex(ValueError, 'body/' + field):
                    normalize_capture(capture)
        for field, value in [('input', None), ('input', ['bad item']), ('instructions', {}),
                             ('input', [{'role': 4}]), ('input', [{'role': 'user', 'content': {}}]),
                             ('input', [{'role': 'user', 'content': [42]}])]:
            with self.subTest(field=field, value=value):
                capture = fixture('responses-a')
                capture['body'][field] = value
                with self.assertRaisesRegex(ValueError, 'body/' + field):
                    normalize_capture(capture)

    def test_wrong_declared_formats_and_missing_input(self):
        for name, wire_format in [('anthropic-a', 'openai-responses'), ('responses-a', 'anthropic-messages')]:
            capture = fixture(name)
            capture['wire_format'] = wire_format
            with self.assertRaisesRegex(ValueError, 'body/'):
                normalize_capture(capture)
        capture = fixture('responses-a')
        del capture['body']['input']
        with self.assertRaisesRegex(ValueError, 'body/input'):
            normalize_capture(capture)

    def test_nonfinite_duplicate_keys_nonstring_keys_and_nonjson_values(self):
        for raw in ['{"a":1,"a":2}', '{"outer":{"a":1,"a":2}}', '{"a":NaN}', '{"a":Infinity}', '{"a":1e999}']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_capture_json(raw)
        for value in [float('nan'), float('inf'), {1: 'key'}, ('tuple',), b'bytes']:
            capture = fixture()
            capture['body']['future'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_capture(capture)
        capture = fixture()
        capture['body']['cycle'] = capture
        with self.assertRaisesRegex(ValueError, 'cyclic'):
            normalize_capture(capture)

    def test_no_external_reference_reading(self):
        capture = fixture('responses-a')
        capture['body']['body_ref'] = 'file:///SYNTHETIC/NEVER_READ'
        capture['body']['metadata'] = {'path': 'https://invalid.example/synthetic'}
        with patch('builtins.open', side_effect=AssertionError('no file reads')):
            result = normalize_capture(capture)
        self.assertEqual(result['request_parameters']['body_ref'], capture['body']['body_ref'])

    def test_markdown_contains_exact_values_and_fence_safety(self):
        capture = fixture()
        capture['body']['system'][0]['text'] = '  原文\n```\n~~~\n尾行\n'
        result = normalize_capture(capture)
        text = render_markdown(result)
        self.assertIn(json.dumps(result['sections'][0]['value'], ensure_ascii=False, indent=2), text)
        self.assertIn('````json', text)
        self.assertIn('NOT_ASSESSED', text)
        self.assertIn('unknown', text)
        self.assertIn('未经独立 runtime 验证', text)
        comparison = compare_observations(result, observe('anthropic-b'))
        markdown = render_markdown(comparison)
        self.assertIn('Baseline', markdown)
        self.assertIn('Candidate', markdown)
        self.assertIn('modified', markdown)
        self.assertIn('synthetic-anthropic-b', markdown)


class ComparisonTests(unittest.TestCase):
    def test_pointer_alignment_and_conditions_changes(self):
        a, b = observe(), observe('anthropic-b')
        before = deepcopy((a, b))
        result = compare_observations(a, b)
        self.assertEqual((a, b), before)
        self.assertEqual(result['alignment'], 'same_format_json_pointer')
        self.assertFalse(result['request_body_equal'])
        self.assertEqual(result['runtime_changes'], ['mode', 'candidate'])
        self.assertEqual(result['changed_top_level_fields'], ['messages', 'system', 'tools'])
        rows = {s['pointer']: s for s in result['sections']}
        self.assertEqual(rows['/system']['change'], 'modified')
        self.assertEqual(rows['/messages/0']['change'], 'unchanged')
        self.assertEqual(rows['/messages/4']['change'], 'added')
        self.assertEqual(rows['/tools/0']['change'], 'modified')
        self.assertEqual(result['baseline'], a)
        result['baseline']['request_body']['model'] = 'MUTATED'
        self.assertEqual(a['request_body']['model'], 'MODEL_PLACEHOLDER')

    def test_cross_format_never_auto_pairs_even_identical_text(self):
        a, b = fixture(), fixture('responses-a')
        a['body']['system'] = 'same text'
        b['body']['instructions'] = 'same text'
        a, b = normalize_capture(a), normalize_capture(b)
        result = compare_observations(a, b)
        self.assertEqual(result['alignment'], 'cross_format_unaligned')
        self.assertEqual(len(result['sections']), len(a['sections']) + len(b['sections']))
        for row in result['sections']:
            self.assertIn(row['change'], ('added', 'removed'))
            self.assertTrue(row['baseline'] is None or row['candidate'] is None)

    def test_missing_empty_arrays_null_and_false_differ(self):
        a = fixture()
        del a['body']['tools']
        b = deepcopy(a)
        b['body']['tools'] = []
        b['body']['optional'] = None
        result = compare_observations(normalize_capture(a), normalize_capture(b))
        self.assertEqual(result['changed_top_level_fields'], ['optional', 'tools'])
        self.assertFalse(result['request_body_equal'])
        self.assertNotIn('/tools', [r['pointer'] for r in result['sections']])
        a['body']['flag'], b['body']['flag'] = False, 0
        self.assertIn('flag', compare_observations(normalize_capture(a), normalize_capture(b))['changed_top_level_fields'])

    def test_whitespace_array_order_significant_object_key_order_irrelevant(self):
        a = fixture()
        b = deepcopy(a)
        b['body'] = dict(reversed(list(b['body'].items())))
        self.assertTrue(compare_observations(normalize_capture(a), normalize_capture(b))['request_body_equal'])
        b['body']['messages'].reverse()
        self.assertIn('messages', compare_observations(normalize_capture(a), normalize_capture(b))['changed_top_level_fields'])
        b = deepcopy(a)
        b['body']['system'][0]['text'] += ' '
        self.assertIn('system', compare_observations(normalize_capture(a), normalize_capture(b))['changed_top_level_fields'])

    def test_pointer_does_not_track_moved_source(self):
        a = fixture()
        b = deepcopy(a)
        b['body']['messages'].insert(0, {'role': 'user', 'content': 'New synthetic first item'})
        result = compare_observations(normalize_capture(a), normalize_capture(b))
        self.assertEqual(next(row for row in result['sections'] if row['pointer'] == '/messages/0')['change'], 'modified')

    def test_every_runtime_label_change_and_removed_sections_are_explicit(self):
        a = fixture()
        b = deepcopy(a)
        b['runtime'] = {key: 'synthetic-changed-' + key for key in a['runtime']}
        b['body']['messages'].pop()
        result = compare_observations(normalize_capture(a), normalize_capture(b))
        self.assertEqual(result['runtime_changes'], ['harness', 'version', 'entrypoint', 'mode', 'candidate', 'session_path'])
        removed = next(row for row in result['sections'] if row['pointer'] == '/messages/3')
        self.assertEqual(removed['change'], 'removed')
        self.assertIsNone(removed['candidate'])
        self.assertEqual(removed['baseline']['value'], a['body']['messages'][3])

    def test_reject_tampered_normalized_claim(self):
        a = observe()
        b = deepcopy(a)
        b['evidence']['model_behavior'] = 'VERIFIED'
        with self.assertRaisesRegex(ValueError, 'unmodified'):
            compare_observations(a, b)


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(CLI), *map(str, args)], cwd=ROOT,
                              capture_output=True, text=True, timeout=15)

    def test_cli_single_and_comparison_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for comparison in (False, True):
                with self.subTest(comparison=comparison):
                    out = base / str(comparison)
                    args = [FIXTURES / 'responses-a.json', '--out', out]
                    if comparison:
                        args += ['--compare', FIXTURES / 'responses-b.json']
                    process = self.run_cli(*args)
                    self.assertEqual(process.returncode, 0, process.stderr)
                    name = 'comparison.json' if comparison else 'observation.json'
                    report = json.loads((out / name).read_text(encoding='utf-8'))
                    expected = compare_observations(observe('responses-a'), observe('responses-b')) if comparison else observe('responses-a')
                    self.assertEqual(report, expected)
                    self.assertEqual((out / 'report.md').read_text(encoding='utf-8'), render_markdown(report))
                    self.assertTrue(json.loads(process.stdout)['input_preserved'])

    def test_invalid_inputs_leave_existing_reports_and_new_directory_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            incoming = base / 'input.json'
            existing = base / 'existing'
            existing.mkdir()
            (existing / 'observation.json').write_text('keep-json')
            (existing / 'report.md').write_text('keep-markdown')
            for raw in ['{', '{"schema":"bad"}', '{"body":1,"body":2}', '{"body":NaN}',
                        json.dumps({**fixture(), 'body': {**fixture()['body'], 'surrogate': '\ud800'}})]:
                incoming.write_text(raw)
                for out in (existing, base / 'never-created'):
                    with self.subTest(raw=raw, out=out.name):
                        process = self.run_cli(incoming, '--out', out)
                        self.assertEqual(process.returncode, 2, process.stdout)
                        self.assertEqual((existing / 'observation.json').read_text(), 'keep-json')
                        self.assertEqual((existing / 'report.md').read_text(), 'keep-markdown')
                        self.assertFalse((base / 'never-created').exists())

    def test_alias_protection_for_both_inputs_and_both_outputs(self):
        for link_type in ('samepath', 'symlink', 'hardlink'):
            for compare in (False, True):
                for target_name in (('comparison.json' if compare else 'observation.json'), 'report.md'):
                    with self.subTest(link_type=link_type, compare=compare, target=target_name), tempfile.TemporaryDirectory() as directory:
                        base = Path(directory)
                        out = base / 'out'
                        out.mkdir()
                        incoming = out / target_name if link_type == 'samepath' else base / 'input.json'
                        original = (FIXTURES / 'anthropic-a.json').read_bytes()
                        incoming.write_bytes(original)
                        target = out / target_name
                        if link_type == 'symlink':
                            target.symlink_to(incoming)
                        elif link_type == 'hardlink':
                            os.link(incoming, target)
                        args = [FIXTURES / 'responses-a.json', '--compare', incoming] if compare else [incoming]
                        process = self.run_cli(*args, '--out', out)
                        self.assertEqual(process.returncode, 2, process.stdout)
                        self.assertEqual(incoming.read_bytes(), original)
                        self.assertEqual(sorted(p.name for p in out.iterdir()), [target_name])

    def test_outputs_alias_each_other_and_nonfiles_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            out = base / 'out'
            out.mkdir()
            first, second = out / 'observation.json', out / 'report.md'
            first.write_text('keep')
            os.link(first, second)
            process = self.run_cli(FIXTURES / 'anthropic-a.json', '--out', out)
            self.assertEqual(process.returncode, 2)
            self.assertIn('alias', process.stderr)
            self.assertEqual(first.read_text(), 'keep')
        for name in ('observation.json', 'report.md'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                out = Path(directory)
                (out / name).mkdir()
                process = self.run_cli(FIXTURES / 'anthropic-a.json', '--out', out)
                self.assertEqual(process.returncode, 2)
                self.assertEqual(len(list(out.iterdir())), 1)

    def test_unrelated_and_dangling_output_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for existing in (False, True):
                with self.subTest(existing=existing):
                    out = base / str(existing)
                    out.mkdir()
                    outside = base / ('outside-' + str(existing))
                    if existing:
                        outside.write_text('keep')
                    (out / 'report.md').symlink_to(outside)
                    process = self.run_cli(FIXTURES / 'anthropic-a.json', '--out', out)
                    self.assertEqual(process.returncode, 2)
                    self.assertFalse((out / 'observation.json').exists())
                    self.assertEqual(outside.read_text() if existing else outside.exists(), 'keep' if existing else False)

    def test_render_failure_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'not-created'
            with patch.object(cli, 'render_markdown', side_effect=ValueError('synthetic render failure')):
                self.assertEqual(cli.main([str(FIXTURES / 'anthropic-a.json'), '--out', str(out)]), 2)
            self.assertFalse(out.exists())

    def test_missing_input_and_bad_output_directory_return_two(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            out = base / 'no-output'
            process = self.run_cli(base / 'missing.json', '--out', out)
            self.assertEqual(process.returncode, 2)
            self.assertFalse(out.exists())
            out.write_text('keep')
            process = self.run_cli(FIXTURES / 'anthropic-a.json', '--out', out)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(out.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
