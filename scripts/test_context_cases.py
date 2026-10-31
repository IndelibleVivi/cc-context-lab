#!/usr/bin/env python3
"""Pure contract and CLI checks for durable context cases.

All capture bodies and companion fixtures are synthetic. No provider, runtime,
live history, scheduler or external delivery is consulted.
"""

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
ENGINE_DIR = ROOT / 'experiments' / 'companion-input'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ENGINE_DIR))

import context_study
from context_lab.case_demo import make_demo_case
from context_lab.cases import render_markdown, run_case, validate_case

CLI = ROOT / 'scripts' / 'run_context_case.py'
SPEC = importlib.util.spec_from_file_location('run_context_case', CLI)
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def capture(capture_id='A', body=None):
    return {
        'schema': 'harness-context-capture/1',
        'capture_id': capture_id,
        'evidence': {'kind': 'synthetic_fixture', 'observed_at': None},
        'runtime': {
            'harness': 'synthetic-test-harness',
            'version': 'synthetic',
            'entrypoint': 'unit-test',
            'mode': 'offline',
            'candidate': 'synthetic-case-test',
            'session_path': None,
        },
        'wire_format': 'anthropic-messages',
        'body': deepcopy(body if body is not None else {
            'model': 'synthetic-model-placeholder',
            'system': [{'type': 'text', 'text': '  Owned core\n尾行  '}],
            'messages': [{'role': 'user', 'content': 'question'}],
            'tools': [{'name': 'synthetic_tool',
                       'input_schema': {'required': ['a']}}],
        }),
    }


def partial_capture(capture_id='P', body=None, observed_fields=None):
    value = capture(capture_id, body if body is not None else {
        'model': 'synthetic-model-placeholder',
        'system': [{'type': 'text', 'text': 'Synthetic partial system.'}],
        'tools': [{'name': 'synthetic_tool',
                   'input_schema': {'type': 'object'}}],
    })
    value['evidence_scope'] = {
        'request_body': 'partial',
        'observed_fields': observed_fields or sorted(value['body']),
    }
    return value


def manifest():
    return {
        'schema': 'harness-context-case/1',
        'case_id': 'synthetic-case',
        'title': '合成 context case',
        'question': '显式 body 中保留了什么？',
        'requirements': [{
            'id': 'req_structure',
            'text': '请求结构满足声明条件。',
            'level': 'request_structure',
        }],
        'study_plan': None,
        'steps': [
            {'id': 'A', 'label': '基线', 'capture': capture('capture-a')},
            {'id': 'B', 'label': '候选', 'capture': capture(
                'capture-b', {
                    'model': 'synthetic-model-placeholder',
                    'system': [{'type': 'text',
                                'text': '  Owned core\n尾行  '}],
                    'messages': [
                        {'role': 'user', 'content': 'question'},
                        {'role': 'assistant', 'content': 'new weather 22C'},
                    ],
                    'tools': [{'name': 'synthetic_tool',
                               'input_schema': {'required': ['a', 'b']}}],
                    'optional': None,
                })},
        ],
        'comparisons': [
            {'id': 'cmp_ab', 'baseline': 'A', 'candidate': 'B'},
        ],
        'checks': [],
    }


def add_check(raw, check_id, step_id, pointer, operator, expected,
              requirement_id='req_structure'):
    raw['checks'].append({
        'id': check_id,
        'requirement_id': requirement_id,
        'step_id': step_id,
        'pointer': pointer,
        'operator': operator,
        'expected': expected,
    })


def check(report, check_id):
    return next(row for row in report['checks'] if row['id'] == check_id)


class PureCaseContracts(unittest.TestCase):
    def test_schema_copy_capture_ids_and_unknown_fields_are_strict(self):
        raw = manifest()
        before = deepcopy(raw)
        result = validate_case(raw)
        self.assertEqual(raw, before)
        result['steps'][0]['capture']['body']['system'][0]['text'] = 'changed'
        self.assertEqual(raw, before)

        cases = [
            ('unknown top field', lambda value: value.update(typo=True)),
            ('unknown requirement field',
             lambda value: value['requirements'][0].update(extra=1)),
            ('unknown step field',
             lambda value: value['steps'][0].update(extra=1)),
            ('unknown comparison field',
             lambda value: value['comparisons'][0].update(extra=1)),
            ('empty case_id', lambda value: value.update(case_id=' ')),
            ('empty requirements', lambda value: value.update(requirements=[])),
            ('unknown level',
             lambda value: value['requirements'][0].update(level='verified')),
            ('duplicate requirement',
             lambda value: value['requirements'].append(
                 deepcopy(value['requirements'][0]))),
            ('duplicate step',
             lambda value: value['steps'].append(deepcopy(value['steps'][0]))),
            ('duplicate capture',
             lambda value: value['steps'][1]['capture'].update(
                 capture_id='capture-a')),
            ('same comparison sides',
             lambda value: value['comparisons'][0].update(candidate='A')),
            ('unknown comparison step',
             lambda value: value['comparisons'][0].update(candidate='Z')),
            ('study plan array', lambda value: value.update(study_plan=[])),
            ('capture unknown field',
             lambda value: value['steps'][0]['capture'].update(extra=1)),
            ('nonfinite', lambda value: value.update(case_id=float('inf'))),
            ('native tuple', lambda value: value.update(title=('bad',))),
        ]
        for label, corrupt in cases:
            with self.subTest(label=label):
                value = manifest()
                corrupt(value)
                with self.assertRaises(ValueError):
                    validate_case(value)

    def test_study_plan_shape_only_waits_for_canonical_runner(self):
        raw = manifest()
        raw['study_plan'] = {'schema': 'not-yet-run', 'fixture': {}}
        validate_case(raw)
        calls = []

        def runner(plan):
            calls.append(plan)
            self.assertEqual(plan['schema'], 'not-yet-run')
            plan['fixture']['mutated'] = True
            return {'schema': 'cc-context-study-result/1', 'canonical': True}

        report = run_case(raw, study_runner=runner)
        self.assertEqual(len(calls), 1)
        self.assertNotIn('mutated', raw['study_plan']['fixture'])
        self.assertEqual(report['study'],
                         {'schema': 'cc-context-study-result/1',
                          'canonical': True})
        with self.assertRaisesRegex(ValueError, 'requires'):
            run_case(raw)

    def test_typed_equality_null_missing_false_empty_and_numbers(self):
        raw = manifest()
        body = raw['steps'][1]['capture']['body']
        body['answer'] = None
        body['flag'] = False
        body['items'] = []
        body['one_int'] = 1
        body['one_float'] = 1.0
        body['big'] = 9007199254740993
        add_check(raw, 'null_present', 'B', '/answer', 'equals', None)
        add_check(raw, 'missing_null', 'B', '/never', 'equals', None)
        add_check(raw, 'bool_int', 'B', '/flag', 'equals', 0)
        add_check(raw, 'empty_array', 'B', '/items', 'equals', [])
        add_check(raw, 'int_float', 'B', '/one_int', 'equals', 1.0)
        add_check(raw, 'float_int', 'B', '/one_float', 'equals', 1)
        add_check(raw, 'big_integer', 'B', '/big', 'equals', 9007199254740993)
        add_check(raw, 'present_null', 'B', '/answer', 'exists', None)
        add_check(raw, 'absent_null', 'B', '/answer', 'absent', None)
        report = run_case(raw)
        self.assertEqual(check(report, 'null_present')['status'], 'PASS')
        self.assertTrue(check(report, 'null_present')['actual_present'])
        self.assertIsNone(check(report, 'null_present')['actual'])
        self.assertEqual(check(report, 'missing_null')['status'], 'FAIL')
        self.assertFalse(check(report, 'missing_null')['actual_present'])
        self.assertEqual(check(report, 'bool_int')['status'], 'FAIL')
        self.assertEqual(check(report, 'empty_array')['status'], 'PASS')
        self.assertEqual(check(report, 'int_float')['status'], 'PASS')
        self.assertEqual(check(report, 'float_int')['status'], 'PASS')
        self.assertEqual(check(report, 'big_integer')['status'], 'PASS')
        self.assertEqual(check(report, 'present_null')['status'], 'PASS')
        self.assertEqual(check(report, 'absent_null')['status'], 'FAIL')

    def test_pointer_escape_empty_key_order_arrays_no_normalization(self):
        raw = manifest()
        body = raw['steps'][0]['capture']['body']
        body[''] = 'root empty key'
        body['a/b'] = {'~key': 'value'}
        body['ordered'] = {'x': 1, 'y': 2}
        body['array'] = ['zero', 'one']
        body['text'] = 'Cafe\u0301  weather  '
        add_check(raw, 'empty_key', 'A', '/', 'equals', 'root empty key')
        add_check(raw, 'escape_slash', 'A', '/a~1b/~0key', 'equals', 'value')
        add_check(raw, 'object_order', 'A', '/ordered', 'equals',
                  {'y': 2, 'x': 1})
        add_check(raw, 'array_order', 'A', '/array', 'equals',
                  ['one', 'zero'])
        add_check(raw, 'unicode_exact', 'A', '/text', 'equals',
                  'Cafe\u0301  weather  ')
        add_check(raw, 'unicode_not_normalized', 'A', '/text', 'equals',
                  'Café  weather  ')
        add_check(raw, 'no_trim', 'A', '/text', 'contains_text', 'weather  ')
        add_check(raw, 'root', 'A', '', 'exists', None)
        report = run_case(raw)
        for check_id in ('empty_key', 'escape_slash', 'object_order',
                         'unicode_exact', 'no_trim', 'root'):
            self.assertEqual(check(report, check_id)['status'], 'PASS')
        self.assertEqual(check(report, 'array_order')['status'], 'FAIL')
        self.assertEqual(
            check(report, 'unicode_not_normalized')['status'], 'FAIL')
        for bad in ('a/b', '/a~2b', '#/bad-fragment'):
            with self.subTest(pointer=bad):
                invalid = manifest()
                add_check(invalid, 'bad', 'A', bad, 'exists', None)
                with self.assertRaises(ValueError):
                    validate_case(invalid)

    def test_pointer_literal_symbols_whitespace_and_escaped_tilde_are_not_special_syntax(self):
        raw = manifest()
        body = raw['steps'][0]['capture']['body']
        body.update({'literal#key': 1, '*': 2, '~1': 3, 'spaces': '  '})
        for cid, pointer, expected in [('hash', '/literal#key', 1), ('star', '/*', 2), ('tilde', '/~01', 3)]:
            add_check(raw, cid, 'A', pointer, 'equals', expected)
        add_check(raw, 'space', 'A', '/spaces', 'contains_text', '  ')
        report = run_case(raw)
        self.assertTrue(all(c['status'] == 'PASS' for c in report['checks']))
        body.pop('*')
        self.assertEqual(check(run_case(raw), 'star')['status'], 'FAIL')

    def test_huge_array_index_is_scoped_missing_without_integer_conversion_failure(self):
        raw = manifest();raw['steps'][0]['capture']['body']['array'] = [None]
        index = '9' * 5000
        add_check(raw, 'final', 'A', '/array/' + index, 'absent', None)
        add_check(raw, 'ancestor', 'A', '/array/' + index + '/text', 'absent', None)
        report = run_case(raw)
        self.assertEqual(check(report, 'final')['status'], 'PASS')
        self.assertEqual(check(report, 'ancestor')['status'], 'NOT_ASSESSED')

    def test_markdown_check_values_use_payload_safe_fences(self):
        raw = manifest();literal = '````json\nSYNTHETIC\n````'
        raw['steps'][0]['capture']['body']['text'] = literal
        add_check(raw, 'fence', 'A', '/text', 'equals', literal)
        text = render_markdown(run_case(raw))
        self.assertIn('`````json', text)
        self.assertIn('- expected:\n\n`````json', text)
        self.assertIn('- actual:\n\n`````json', text)

    def test_contains_text_only_accepts_a_resolved_string(self):
        raw = manifest()
        body = raw['steps'][0]['capture']['body']
        body['object'] = {'nested': 'needle'}
        body['number'] = 42
        add_check(raw, 'object_not_stringified', 'A', '/object',
                  'contains_text', 'needle')
        add_check(raw, 'number_not_stringified', 'A', '/number',
                  'contains_text', '42')
        add_check(raw, 'missing_text', 'A', '/missing',
                  'contains_text', 'needle')
        report = run_case(raw)
        for check_id in ('object_not_stringified', 'number_not_stringified'):
            self.assertEqual(check(report, check_id)['status'], 'FAIL')
            self.assertIn('字符串', check(report, check_id)['reason'])
        self.assertEqual(check(report, 'missing_text')['status'], 'FAIL')
        self.assertIn('不存在', check(report, 'missing_text')['reason'])

    def test_traversal_blocks_are_not_evidence_of_absence(self):
        raw = manifest()
        body = raw['steps'][0]['capture']['body']
        body['array'] = []
        body['short'] = ['only']
        body['scalar'] = 'text'
        for pointer in ('/missing/deep', '/array/0/deep', '/array/-',
                        '/array/01', '/array/-1', '/array/x',
                        '/short/1/deep', '/scalar/child'):
            add_check(raw, 'blocked-' + pointer, 'A', pointer, 'absent', None)
        add_check(raw, 'empty_final_index', 'A', '/array/0', 'absent', None)
        add_check(raw, 'out_of_range_final', 'A', '/short/2', 'absent', None)
        add_check(raw, 'final_missing_member', 'A', '/no-such-key',
                  'absent', None)
        report = run_case(raw)
        for row in report['checks']:
            if row['id'].startswith('blocked-'):
                self.assertEqual(row['status'], 'NOT_ASSESSED', row)
                self.assertIsNone(row['actual_present'])
                self.assertIsNone(row['actual'])
        for check_id in ('empty_final_index', 'out_of_range_final',
                         'final_missing_member'):
            self.assertEqual(check(report, check_id)['status'], 'PASS')
            self.assertFalse(check(report, check_id)['actual_present'])
        self.assertIn('显式 request body', ' '.join(report['limitations']))

    def test_missing_capture_comparison_and_requirement_aggregation(self):
        raw = manifest()
        raw['steps'].append({'id': 'M', 'label': '缺失证据', 'capture': None})
        raw['comparisons'].append({
            'id': 'cmp_missing', 'baseline': 'A', 'candidate': 'M'})
        raw['requirements'].extend([
            {'id': 'req_missing', 'text': '缺失证据',
             'level': 'request_structure'},
            {'id': 'req_behavior', 'text': '模型行为',
             'level': 'model_behavior'},
            {'id': 'req_delivery', 'text': '外部交付',
             'level': 'external_delivery'},
        ])
        add_check(raw, 'pass', 'A', '/model', 'exists', None)
        add_check(raw, 'missing', 'M', '/model', 'absent', None,
                  'req_missing')
        report = run_case(raw)
        missing = next(row for row in report['checks']
                       if row['id'] == 'missing')
        self.assertEqual(missing['status'], 'NOT_ASSESSED')
        self.assertIsNone(missing['actual_present'])
        comparison = next(row for row in report['comparisons']
                          if row['id'] == 'cmp_missing')
        self.assertEqual(comparison['status'], 'NOT_ASSESSED')
        self.assertIsNone(comparison['comparison'])
        statuses = {row['id']: row['status']
                    for row in report['requirements']}
        self.assertEqual(statuses, {
            'req_structure': 'PASS',
            'req_missing': 'NOT_ASSESSED',
            'req_behavior': 'NOT_ASSESSED',
            'req_delivery': 'NOT_ASSESSED',
        })
        self.assertEqual(report['summary'],
                         {'passed': 1, 'failed': 0, 'not_assessed': 3})
        self.assertEqual(report['evidence'], {
            'model_behavior': 'NOT_ASSESSED',
            'external_delivery': 'NOT_ASSESSED',
            'chronology': 'DECLARED_NOT_VERIFIED',
        })

    def test_unobserved_messages_are_not_assessed_but_observed_absence_and_empty_array_are(self):
        raw = manifest()
        raw['steps'] = [
            {'id': 'partial', 'label': 'Partial shape',
             'capture': partial_capture('partial-capture')},
            {'id': 'empty', 'label': 'Observed empty messages',
             'capture': partial_capture('empty-capture', {
                 'model': 'synthetic-model-placeholder',
                 'system': [{'type': 'text', 'text': 'Synthetic system.'}],
                 'messages': [],
             }, ['model', 'system', 'messages'])},
            {'id': 'absent', 'label': 'Observed but no messages member',
             'capture': partial_capture('absent-capture', {
                 'model': 'synthetic-model-placeholder',
                 'system': [{'type': 'text', 'text': 'Synthetic system.'}],
             }, ['model', 'system', 'messages'])},
        ]
        raw['comparisons'] = []
        raw['checks'] = []
        add_check(raw, 'partial_absent', 'partial', '/messages',
                  'absent', None)
        add_check(raw, 'partial_exists', 'partial', '/messages',
                  'exists', None)
        add_check(raw, 'empty_absent', 'empty', '/messages', 'absent', None)
        add_check(raw, 'empty_equals', 'empty', '/messages', 'equals', [])
        add_check(raw, 'empty_child', 'empty', '/messages/0', 'absent', None)
        add_check(raw, 'absent_absent', 'absent', '/messages', 'absent', None)
        report = run_case(raw)
        for check_id in ('partial_absent', 'partial_exists'):
            row = check(report, check_id)
            self.assertEqual(row['status'], 'NOT_ASSESSED', check_id)
            self.assertIsNone(row['actual_present'])
            self.assertIsNone(row['actual'])
            self.assertEqual(row['scope_reason'], 'unobserved_field')
            self.assertIn('未观察', row['reason'])
        self.assertEqual(check(report, 'empty_absent')['status'], 'FAIL')
        self.assertTrue(check(report, 'empty_absent')['actual_present'])
        self.assertEqual(check(report, 'empty_absent')['scope_reason'],
                         'observed')
        self.assertEqual(check(report, 'empty_equals')['status'], 'PASS')
        self.assertEqual(check(report, 'empty_child')['status'], 'PASS')
        self.assertFalse(check(report, 'empty_child')['actual_present'])
        self.assertEqual(check(report, 'absent_absent')['status'], 'PASS')
        self.assertFalse(check(report, 'absent_absent')['actual_present'])
        self.assertEqual(report['requirements'][0]['status'], 'FAIL')
        self.assertEqual(report['summary']['failed'], 1)
        partial = next(step for step in report['steps']
                       if step['id'] == 'partial')['observation']
        self.assertEqual(partial['evidence_scope']['request_body'],
                         'partial')
        self.assertNotIn('messages', partial['request_body'])
        text = render_markdown(report)
        self.assertIn('声明的部分原始 request body', text)
        self.assertIn('未观察不等于字段不存在', text)
        self.assertIn('server/provider 注入', text)

        unobserved_only = manifest()
        unobserved_only['steps'] = [
            {'id': 'partial', 'label': 'Partial shape',
             'capture': partial_capture('partial-only-capture')},
        ]
        unobserved_only['comparisons'] = []
        unobserved_only['checks'] = []
        add_check(unobserved_only, 'unobserved_absent', 'partial',
                  '/messages', 'absent', None)
        unobserved_report = run_case(unobserved_only)
        self.assertEqual(
            unobserved_report['checks'][0]['status'], 'NOT_ASSESSED')
        self.assertEqual(
            unobserved_report['requirements'][0]['status'], 'NOT_ASSESSED')
        self.assertEqual(unobserved_report['summary'], {
            'passed': 0, 'failed': 0, 'not_assessed': 1,
        })

    def test_partial_body_root_checks_never_claim_the_capture_file_exists(self):
        raw = manifest()
        raw['steps'] = [
            {'id': 'partial', 'label': 'Partial shape',
             'capture': partial_capture('partial-root-capture')},
            {'id': 'complete', 'label': 'Complete shape',
             'capture': capture('complete-root-capture')},
        ]
        raw['comparisons'] = []
        raw['checks'] = []
        for operator, expected in (
                ('exists', None), ('absent', None),
                ('equals', {'model': 'synthetic-model-placeholder'})):
            add_check(raw, 'partial_' + operator, 'partial', '',
                      operator, expected)
        add_check(raw, 'complete_root', 'complete', '', 'exists', None)
        report = run_case(raw)
        for operator in ('exists', 'absent', 'equals'):
            row = check(report, 'partial_' + operator)
            self.assertEqual(row['status'], 'NOT_ASSESSED')
            self.assertIsNone(row['actual_present'])
            self.assertIsNone(row['actual'])
            self.assertEqual(row['scope_reason'], 'partial_body_root')
        self.assertEqual(check(report, 'complete_root')['status'], 'PASS')
        self.assertEqual(check(report, 'complete_root')['scope_reason'],
                         'observed')
        self.assertEqual(report['requirements'][0]['status'],
                         'NOT_ASSESSED')

    def test_requirement_precedence_and_non_structure_checks_rejected(self):
        raw = manifest()
        add_check(raw, 'fail', 'A', '/missing', 'exists', None)
        report = run_case(raw)
        self.assertEqual(report['requirements'][0]['status'], 'FAIL')
        self.assertEqual(report['summary']['failed'], 1)

        raw['checks'][0]['operator'] = 'contains_text'
        raw['checks'][0]['expected'] = 42
        with self.assertRaises(ValueError):
            validate_case(raw)
        raw = manifest()
        raw['requirements'].append({
            'id': 'req_behavior', 'text': '行为',
            'level': 'model_behavior'})
        add_check(raw, 'bad_behavior', 'A', '/model', 'exists', None,
                  'req_behavior')
        with self.assertRaisesRegex(ValueError, 'request_structure'):
            validate_case(raw)

    def test_no_checks_means_not_assessed(self):
        report = run_case(manifest())
        self.assertEqual(report['requirements'][0]['status'], 'NOT_ASSESSED')
        self.assertEqual(report['summary'],
                         {'passed': 0, 'failed': 0, 'not_assessed': 1})

    def test_run_is_pure_and_markdown_keeps_exact_values(self):
        raw = manifest()
        raw['steps'][0]['capture']['body']['system'][0]['text'] = (
            '  Owned core\n```\n尾行  ')
        before = deepcopy(raw)
        report = run_case(raw)
        self.assertEqual(raw, before)
        report['steps'][0]['observation']['request_body']['system'][0][
            'text'] = 'mutated'
        self.assertEqual(raw, before)
        text = render_markdown(report)
        self.assertIn(raw['question'], text)
        self.assertIn('````json', text)
        self.assertIn('完整原始 request body', text)
        self.assertIn('DECLARED_NOT_VERIFIED', text)
        self.assertIn('缺失', text)
        self.assertNotIn('<html', text.lower())

        raw['checks'] = [
            {'id': 'nullcheck', 'requirement_id': 'req_structure',
             'step_id': 'B', 'pointer': '/optional', 'operator': 'equals',
             'expected': None},
            {'id': 'missingcheck', 'requirement_id': 'req_structure',
             'step_id': 'B', 'pointer': '/never', 'operator': 'equals',
             'expected': None},
        ]
        report = run_case(raw)
        text = render_markdown(report)
        self.assertIn('actual: `<MISSING>`', text)
        self.assertIn('actual: `null`', text)

    def test_demo_is_authored_and_exercises_research_states(self):
        fixture = json.loads(
            (ENGINE_DIR / 'fixtures' / 'common_scenario.json').read_text(
                encoding='utf-8'))
        demo = make_demo_case(fixture)
        self.assertEqual(len([
            step for step in demo['steps'] if step['capture'] is not None
        ]), 6)
        self.assertEqual(demo['study_plan']['baseline'], {
            'policy_id': 'P1_fixed_interval',
            'placement_id': 'PL_main_defer',
            'history_mode': 'same'})
        self.assertEqual(demo['study_plan']['candidate']['history_mode'],
                         'fresh')
        self.assertEqual(len(demo['comparisons']), 3)
        self.assertTrue(any(step['capture'] is None for step in demo['steps']))
        report = run_case(demo, study_runner=context_study.run_study)
        rows = {row['id']: row['status'] for row in report['checks']}
        for check_id in ('core_retained', 'weather_updated', 'recall_original',
                         'old_weather_historical', 'fresh_carryover',
                         'tool_schema_preserved'):
            self.assertEqual(rows[check_id], 'PASS', check_id)
        self.assertEqual(rows['initial_schema_failure'], 'FAIL')
        self.assertEqual(rows['missing_capture_is_not_absent'],
                         'NOT_ASSESSED')
        self.assertEqual(report['study']['schema'],
                         'cc-context-study-result/1')
        self.assertEqual(report['evidence']['chronology'],
                         'DECLARED_NOT_VERIFIED')
        self.assertEqual(report['summary']['failed'], 1)
        self.assertEqual(report['summary']['not_assessed'], 3)
        text = render_markdown(report)
        self.assertIn('association declared only', text.lower())


class CliContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='context-case-test-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def write_case(self, path, value=None):
        text = json.dumps(value or manifest(), ensure_ascii=False,
                          separators=(',', ':')) + '  \n'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path.read_bytes()

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            cwd=ROOT, capture_output=True, text=True, timeout=90)

    def test_cli_exit_zero_for_not_assessed_and_one_for_failure(self):
        incoming = self.directory / 'incoming.json'
        self.write_case(incoming)
        out = self.directory / 'zero'
        result = self.run_cli(incoming, '--out', out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            {path.name for path in out.iterdir()},
            {'case.json', 'report.json', 'report.md'})
        stdout = json.loads(result.stdout)
        self.assertFalse(stdout['readiness_claim'])

        failing = manifest()
        add_check(failing, 'failure', 'A', '/missing', 'exists', None)
        failing_path = self.directory / 'failing.json'
        self.write_case(failing_path, failing)
        failing_out = self.directory / 'one'
        result = self.run_cli(failing_path, '--out', failing_out)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)['status'],
            'scoped_requirement_failure')
        self.assertTrue((failing_out / 'report.json').is_file())

    def test_cli_invalid_inputs_exit_two_without_creating_output(self):
        raw = manifest()
        raw['unknown'] = True
        duplicate = ('{"schema": "harness-context-case/1", '
                     '"schema": "harness-context-case/1"}')
        for index, content in enumerate((
                '{"broken":', '{"number": NaN}', duplicate,
                json.dumps(raw), json.dumps({**manifest(),
                                             'checks': [{'id': 'x'}]}))):
            with self.subTest(index=index):
                incoming = self.directory / ('invalid-%d.json' % index)
                incoming.write_text(content, encoding='utf-8')
                out = self.directory / ('invalid-out-%d' % index)
                result = self.run_cli(incoming, '--out', out)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(out.exists())
                self.assertEqual(incoming.read_text(encoding='utf-8'), content)

    def test_in_place_case_is_preserved_byte_for_byte(self):
        out = self.directory / 'in-place'
        incoming = out / 'case.json'
        original = self.write_case(incoming)
        result = self.run_cli(incoming, '--out', out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(incoming.read_bytes(), original)
        self.assertEqual({path.name for path in out.iterdir()},
                         {'case.json', 'report.json', 'report.md'})
        report = json.loads((out / 'report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['case'], json.loads(original))

    def test_input_and_output_aliases_nonfiles_are_rejected_before_writes(self):
        for filename in ('report.json', 'report.md'):
            with self.subTest(filename=filename):
                out = self.directory / ('alias-' + filename.replace('.', '-'))
                incoming = out / filename
                original = self.write_case(incoming)
                result = self.run_cli(incoming, '--out', out)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn('aliases', result.stderr)
                self.assertEqual(incoming.read_bytes(), original)
                self.assertEqual({path.name for path in out.iterdir()},
                                 {filename})

        for kind in ('symlink', 'hardlink'):
            with self.subTest(kind=kind):
                out = self.directory / ('link-' + kind)
                out.mkdir()
                incoming = self.directory / ('input-' + kind + '.json')
                original = self.write_case(incoming)
                target = out / 'report.json'
                if kind == 'symlink':
                    target.symlink_to(incoming)
                else:
                    os.link(incoming, target)
                result = self.run_cli(incoming, '--out', out)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(incoming.read_bytes(), original)
                self.assertEqual({path.name for path in out.iterdir()},
                                 {'report.json'})

        out = self.directory / 'mutual'
        out.mkdir()
        first, second = out / 'report.json', out / 'report.md'
        first.write_text('keep', encoding='utf-8')
        os.link(first, second)
        incoming = self.directory / 'mutual-input.json'
        self.write_case(incoming)
        result = self.run_cli(incoming, '--out', out)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(first.read_text(encoding='utf-8'), 'keep')

        nonfile = self.directory / 'nonfile'
        (nonfile / 'report.md').mkdir(parents=True)
        result = self.run_cli(incoming, '--out', nonfile)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse((nonfile / 'case.json').exists())

    def test_failure_preserves_previous_reports_and_prechecks_encoding(self):
        incoming = self.directory / 'incoming.json'
        self.write_case(incoming)
        out = self.directory / 'existing'
        out.mkdir()
        for name in ('case.json', 'report.json', 'report.md'):
            (out / name).write_text('KEEP ' + name, encoding='utf-8')
        invalid = manifest()
        invalid['title'] = '\ud800'
        bad_input = self.directory / 'surrogate.json'
        bad_input.write_text(
            json.dumps(invalid, ensure_ascii=True), encoding='utf-8')
        result = self.run_cli(bad_input, '--out', out)
        self.assertEqual(result.returncode, 2, result.stderr)
        for name in ('case.json', 'report.json', 'report.md'):
            self.assertEqual((out / name).read_text(encoding='utf-8'),
                             'KEEP ' + name)

        with patch.object(cli, 'render_markdown',
                          side_effect=ValueError('synthetic render failure')):
            self.assertEqual(
                cli.main([str(incoming), '--out', str(out)]), 2)
        for name in ('case.json', 'report.json', 'report.md'):
            self.assertEqual((out / name).read_text(encoding='utf-8'),
                             'KEEP ' + name)

    def test_private_output_requires_external_or_git_ignored_directory(self):
        external = self.directory / 'external'
        self.write_case(self.directory / 'input.json')
        with patch.object(cli.subprocess, 'run',
                          side_effect=AssertionError('external needs no git')):
            self.assertEqual(
                cli.main([str(self.directory / 'input.json'),
                          '--out', str(external)]), 0)

        with patch.object(cli.subprocess, 'run') as git_check:
            git_check.return_value.returncode = 1
            with patch.object(cli, 'run_case') as run:
                self.assertEqual(
                    cli.main([str(self.directory / 'input.json'),
                              '--out',
                              str(ROOT / 'not-ignored-context-case-output')]),
                    2)
                run.assert_not_called()
            self.assertEqual(git_check.call_args.args[0][:3],
                             ['git', 'check-ignore', '--quiet'])
        self.assertFalse((ROOT / 'not-ignored-context-case-output').exists())

    def test_study_failure_and_render_failure_preserve_outputs(self):
        out = self.directory / 'study-out'
        out.mkdir()
        (out / 'report.json').write_text('KEEP', encoding='utf-8')
        raw = manifest()
        raw['study_plan'] = {
            'schema': 'cc-context-study/1', 'title': 'invalid',
            'question': 'invalid', 'preserve': [], 'fixture': {},
            'baseline': {}, 'candidate': {},
        }
        incoming = self.directory / 'study.json'
        self.write_case(incoming, raw)
        result = self.run_cli(incoming, '--out', out)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual((out / 'report.json').read_text(), 'KEEP')
        self.assertFalse((out / 'case.json').exists())

    def test_demo_cli_and_argument_selection(self):
        out = self.directory / 'demo'
        result = self.run_cli('--demo', '--out', out)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual({path.name for path in out.iterdir()},
                         {'case.json', 'report.json', 'report.md'})
        report = json.loads((out / 'report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['schema'], 'harness-context-case-result/1')
        self.assertEqual(report['summary']['failed'], 1)
        self.assertEqual(
            next(row for row in report['checks']
                 if row['id'] == 'missing_capture_is_not_absent')['status'],
            'NOT_ASSESSED')

        for args in ((), ('--demo', str(self.directory / 'input.json'))):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
