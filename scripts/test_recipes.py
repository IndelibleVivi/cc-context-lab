#!/usr/bin/env python3
"""Contract tests for authored CC recipes; all material is synthetic/offline."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from context_lab import cases, recipes


RUNNER = ROOT / 'scripts' / 'run_context_case.py'
EXPECTED_IDS = ('owned-core', 'dynamic-state', 'compact-resume')


def statuses(report, kind):
    return {row['id']: row['status'] for row in report[kind]}


def check(report, check_id):
    return next(row for row in report['checks'] if row['id'] == check_id)


def step_case(recipe_id):
    return recipes.load_recipe_case(recipe_id)


class CatalogContracts(unittest.TestCase):
    def test_catalog_is_strict_exact_and_self_contained(self):
        first = recipes.load_catalog()
        second = recipes.load_catalog()
        self.assertEqual(first, second)
        self.assertEqual(first['schema'], 'cc-context-recipes/1')
        self.assertEqual(
            tuple(row['id'] for row in first['recipes']), EXPECTED_IDS)
        for recipe in first['recipes']:
            self.assertEqual(recipe['native_status'], 'NOT_ASSESSED')
            self.assertTrue(recipe['expected_checks'])
            self.assertTrue(recipe['expected_requirements'])
            case = recipes.load_recipe_case(recipe['id'])
            self.assertEqual(case['schema'], 'harness-context-case/1')
            self.assertIsNone(case['study_plan'])
            self.assertTrue(case['steps'])
            for step in case['steps']:
                self.assertIsNotNone(step['capture'])
                self.assertEqual(
                    step['capture']['evidence']['kind'], 'synthetic_fixture')
            self.assertNotIn('body', json.dumps(recipe))

        first['recipes'][0]['title'] = 'mutated'
        self.assertNotEqual(first, recipes.load_catalog())

    def test_every_declared_status_matches_canonical_case_engine(self):
        for recipe in recipes.load_catalog()['recipes']:
            with self.subTest(recipe=recipe['id']):
                report = cases.run_case(
                    recipes.load_recipe_case(recipe['id']))
                self.assertEqual(
                    statuses(report, 'checks'), recipe['expected_checks'])
                self.assertEqual(
                    statuses(report, 'requirements'),
                    recipe['expected_requirements'])
                self.assertGreater(report['summary']['failed'], 0)
                self.assertGreater(report['summary']['not_assessed'], 0)
                self.assertEqual(
                    report['evidence']['model_behavior'], 'NOT_ASSESSED')
                self.assertEqual(
                    report['evidence']['external_delivery'], 'NOT_ASSESSED')
                self.assertEqual(
                    report['evidence']['chronology'],
                    'DECLARED_NOT_VERIFIED')

    def test_each_recipe_declares_baseline_stale_and_fixed_or_equivalent(self):
        steps = {
            recipe_id: [step['id'] for step in step_case(recipe_id)['steps']]
            for recipe_id in EXPECTED_IDS
        }
        self.assertEqual(steps['owned-core'], ['baseline', 'stripped', 'fixed'])
        self.assertEqual(
            steps['dynamic-state'],
            ['baseline', 'stale', 'history_dropped', 'fixed'])
        self.assertEqual(
            steps['compact-resume'],
            ['baseline', 'compacted_stale', 'compacted_fixed',
             'partial_system_tools'])

    def test_catalog_rejects_unknown_schema_fields_paths_and_expectations(self):
        with tempfile.TemporaryDirectory(prefix='recipe-catalog-test-') as temp:
            root = Path(temp)
            source = ROOT
            for relative in (
                    'references/recipes.json',
                    'experiments/recipes/cases/owned-core.json',
                    'experiments/recipes/cases/dynamic-state.json',
                    'experiments/recipes/cases/compact-resume.json',
                    'docs/handbook/owned-core.md',
                    'docs/handbook/dynamic-state.md',
                    'docs/handbook/compact-resume.md',
                    'context_lab/observations.py'):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((source / relative).read_bytes())

            base = json.loads(
                (root / 'references/recipes.json').read_text(encoding='utf-8'))
            mutations = []

            def changed(mutator):
                value = deepcopy(base)
                mutator(value)
                return value

            mutations.append((
                'unknown top field',
                changed(lambda value: value.update(extra=True)),
            ))
            mutations.append((
                'wrong schema',
                changed(lambda value: value.update(schema='other/1')),
            ))
            mutations.append((
                'unknown recipe field',
                changed(lambda value: value['recipes'][0].update(extra=True)),
            ))
            mutations.append((
                'wrong IDs',
                changed(lambda value: value['recipes'].reverse()),
            ))
            mutations.append((
                'escape path',
                changed(lambda value: value['recipes'][0].update(
                    case_path='../outside.json')),
            ))
            mutations.append((
                'absolute path',
                changed(lambda value: value['recipes'][0].update(
                    guide_path='/tmp/guide.md')),
            ))
            mutations.append((
                'missing source',
                changed(lambda value: value['recipes'][0]['mechanisms'][0]
                        .update(sources=['docs/missing.md'])),
            ))
            mutations.append((
                'wrong expected check',
                changed(lambda value: value['recipes'][0]['expected_checks']
                        .update(core_retained_after_strip='FAIL')),
            ))
            mutations.append((
                'missing expected check',
                changed(lambda value: value['recipes'][0]['expected_checks']
                        .pop('core_retained_after_strip')),
            ))
            mutations.append((
                'extra expected requirement',
                changed(lambda value: value['recipes'][0]
                        ['expected_requirements'].update(extra='PASS')),
            ))
            mutations.append((
                'native claimed',
                changed(lambda value: value['recipes'][0].update(
                    native_status='PASS')),
            ))
            mutations.append((
                'invalid status',
                changed(lambda value: value['recipes'][0]['expected_checks']
                        .update(core_retained_after_strip='UNKNOWN')),
            ))
            for label, value in mutations:
                with self.subTest(label=label):
                    (root / 'references/recipes.json').write_text(
                        json.dumps(value), encoding='utf-8')
                    with self.assertRaises(ValueError):
                        recipes.load_catalog(root)

    def test_strict_reader_rejects_duplicate_keys_and_functions_reject_unknown_ids(self):
        with tempfile.TemporaryDirectory(prefix='recipe-strict-test-') as temp:
            root = Path(temp)
            (root / 'references').mkdir()
            (root / 'references/recipes.json').write_text(
                '{"schema":"cc-context-recipes/1",'
                '"schema":"cc-context-recipes/1","recipes":[]}',
                encoding='utf-8',
            )
            with self.assertRaises(ValueError):
                recipes.load_catalog(root)
        with self.assertRaises(ValueError):
            recipes.load_recipe_case('not-a-recipe')
        with self.assertRaises(ValueError):
            recipes.load_recipe_case(None)


class NegativeValueContracts(unittest.TestCase):
    def assert_changed_check_fails(self, recipe_id, check_id, mutate):
        manifest = step_case(recipe_id)
        mutate(manifest)
        before = cases.run_case(step_case(recipe_id))
        after = cases.run_case(manifest)
        self.assertEqual(check(before, check_id)['status'], 'PASS')
        self.assertEqual(check(after, check_id)['status'], 'FAIL')

    def test_owned_core_changed_values_are_rejected(self):
        def wrong_core(case):
            case['steps'][1]['capture']['body']['system'][0]['text'] = (
                'SYNTHETIC OWNED CORE')

        def wrong_schema(case):
            case['steps'][1]['capture']['body']['tools'][0]['input_schema'][
                'required'] = ['label']

        def wrong_fixed_schema(case):
            case['steps'][2]['capture']['body']['tools'][0]['input_schema'][
                'required'] = ['label']

        def wrong_label_type(case):
            case['steps'][2]['capture']['body']['tools'][0]['input_schema'][
                'properties']['label']['type'] = 'integer'

        def wrong_scope_enum(case):
            case['steps'][2]['capture']['body']['tools'][0]['input_schema'][
                'properties']['scope']['enum'] = ['archive']

        def wrong_additional_properties(case):
            case['steps'][2]['capture']['body']['tools'][0]['input_schema'][
                'additionalProperties'] = True

        def wrong_tool_name(case):
            case['steps'][2]['capture']['body']['tools'][0][
                'name'] = 'synthetic_archive_guess'

        def wrong_guidance(case):
            case['steps'][2]['capture']['body']['tools'][0][
                'description'] = 'Different tool guidance.'

        self.assert_changed_check_fails(
            'owned-core', 'core_retained_after_strip', wrong_core)
        self.assert_changed_check_fails(
            'owned-core', 'schema_retained_while_guidance_missing',
            wrong_schema)
        self.assert_changed_check_fails(
            'owned-core', 'schema_retained_after_fix', wrong_fixed_schema)
        self.assert_changed_check_fails(
            'owned-core', 'schema_retained_after_fix', wrong_label_type)
        self.assert_changed_check_fails(
            'owned-core', 'schema_retained_after_fix', wrong_scope_enum)
        self.assert_changed_check_fails(
            'owned-core', 'schema_retained_after_fix',
            wrong_additional_properties)
        self.assert_changed_check_fails(
            'owned-core', 'tool_name_retained_after_fix', wrong_tool_name)
        self.assert_changed_check_fails(
            'owned-core', 'guidance_restored', wrong_guidance)

    def test_dynamic_state_changed_values_are_rejected(self):
        def wrong_current(case):
            case['steps'][3]['capture']['body']['messages'][4][
                'content'] = 'Synthetic ambient snapshot revision 2.'

        def wrong_correction(case):
            case['steps'][3]['capture']['body']['messages'][3][
                'content'] = 'Correction omitted the production scope.'

        def wrong_revision_2_history(case):
            case['steps'][3]['capture']['body']['messages'][2][
                'content'] = 'Ambient state revision 1: the reading lamp is beside the north desk.'

        def rewrite_history(case):
            case['steps'][1]['capture']['body']['messages'][1][
                'content'] = 'Ambient state revision 99.'

        self.assert_changed_check_fails(
            'dynamic-state', 'revision_3_is_current', wrong_current)
        self.assert_changed_check_fails(
            'dynamic-state', 'correction_exact', wrong_correction)
        self.assert_changed_check_fails(
            'dynamic-state', 'revision_2_retained_in_fixed_history',
            wrong_revision_2_history)
        self.assert_changed_check_fails(
            'dynamic-state', 'old_state_retained_in_history', rewrite_history)

    def test_compact_resume_changed_values_are_rejected(self):
        def wrong_old_guidance(case):
            case['steps'][2]['capture']['body']['messages'][0][
                'content'] = 'Different original guidance.'

        def wrong_correction(case):
            case['steps'][2]['capture']['body']['messages'][1][
                'content'] = 'Correction: staging only.'

        def wrong_summary(case):
            case['steps'][2]['capture']['body']['messages'][2][
                'content'] = 'Compact summary: only production.'

        def wrong_resume(case):
            case['steps'][2]['capture']['body']['messages'][3][
                'content'] = 'Stop here.'

        self.assert_changed_check_fails(
            'compact-resume', 'old_guidance_retained', wrong_old_guidance)
        self.assert_changed_check_fails(
            'compact-resume', 'correction_exact', wrong_correction)
        self.assert_changed_check_fails(
            'compact-resume', 'summary_retains_correction', wrong_summary)
        self.assert_changed_check_fails(
            'compact-resume', 'resume_prompt_present', wrong_resume)

    def test_partial_messages_cannot_flip_into_a_claim(self):
        manifest = step_case('compact-resume')
        before = cases.run_case(manifest)
        row = check(before, 'partial_messages_absence_unproven')
        self.assertEqual(row['status'], 'NOT_ASSESSED')
        self.assertEqual(row['scope_reason'], 'unobserved_field')
        self.assertIsNone(row['actual_present'])

        # Declaring a key observed without adding it makes the member known
        # absent, but the requested child pointer is still blocked. It remains
        # distinct from the unobserved form above.
        manifest['steps'][3]['capture']['evidence_scope'][
            'observed_fields'].append('messages')
        observed_absent = cases.run_case(manifest)
        row = check(observed_absent, 'partial_messages_absence_unproven')
        self.assertEqual(row['status'], 'NOT_ASSESSED')
        self.assertEqual(row['scope_reason'], 'blocked_pointer')
        self.assertIsNone(row['actual_present'])

        # An explicitly observed empty array does support a canonical child
        # index being absent; the scope is still partial, not a full capture.
        manifest['steps'][3]['capture']['body']['messages'] = []
        observed_empty = cases.run_case(manifest)
        row = check(observed_empty, 'partial_messages_absence_unproven')
        self.assertEqual(row['status'], 'PASS')
        self.assertFalse(row['actual_present'])
        self.assertEqual(row['scope_reason'], 'observed')
        self.assertEqual(
            observed_empty['steps'][3]['observation']['evidence_scope'][
                'request_body'], 'partial')

    def test_deliberate_counterexamples_can_only_become_pass_by_changing_material(self):
        manifest = step_case('owned-core')
        manifest['steps'][1]['capture']['body']['tools'][0]['description'] = (
            'SYNTHETIC TOOL GUIDANCE: never infer a missing record.')
        self.assertEqual(
            check(cases.run_case(manifest),
                  'missing_guidance_counterexample')['status'], 'PASS')
        original = step_case('owned-core')
        self.assertEqual(
            check(cases.run_case(original),
                  'missing_guidance_counterexample')['status'], 'FAIL')


class CliContracts(unittest.TestCase):
    def run_recipe(self, recipe_id, out):
        return subprocess.run(
            [sys.executable, str(RUNNER),
             str(ROOT / 'experiments/recipes/cases' / (recipe_id + '.json')),
             '--out', str(out)],
            cwd=ROOT, capture_output=True, text=True, timeout=90,
        )

    def test_each_recipe_cli_exits_one_and_retains_failure_report(self):
        with tempfile.TemporaryDirectory(prefix='recipe-cli-test-') as temp:
            for recipe_id in EXPECTED_IDS:
                out = Path(temp) / recipe_id
                result = self.run_recipe(recipe_id, out)
                with self.subTest(recipe=recipe_id):
                    self.assertEqual(result.returncode, 1, result.stderr)
                    summary = json.loads(result.stdout)
                    self.assertEqual(
                        summary['status'], 'scoped_requirement_failure')
                    self.assertFalse(summary['readiness_claim'])
                    self.assertEqual(
                        {path.name for path in out.iterdir()},
                        {'case.json', 'report.json', 'report.md'})
                    report = json.loads(
                        (out / 'report.json').read_text(encoding='utf-8'))
                    expected = next(
                        row for row in recipes.load_catalog()['recipes']
                        if row['id'] == recipe_id)
                    self.assertEqual(
                        statuses(report, 'checks'),
                        expected['expected_checks'])
                    self.assertGreater(report['summary']['failed'], 0)

    def test_runner_exit_two_does_not_create_output_for_invalid_case(self):
        with tempfile.TemporaryDirectory(prefix='recipe-invalid-test-') as temp:
            base = Path(temp)
            invalid = base / 'invalid.json'
            invalid.write_text('{"schema":"harness-context-case/1"}',
                               encoding='utf-8')
            out = base / 'output'
            result = subprocess.run(
                [sys.executable, str(RUNNER), str(invalid),
                 '--out', str(out)],
                cwd=ROOT, capture_output=True, text=True, timeout=90,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
