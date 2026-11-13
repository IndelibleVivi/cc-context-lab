#!/usr/bin/env python3
"""Offline contract tests for recipe mechanism claims and fixed sources."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from context_lab import mechanisms, recipes

EXPECTED_IDS = (
    'owned-core-boundary',
    'tool-schema-guidance',
    'revision-injection',
    'correction-lineage',
    'compact-retention',
    'resume-reload',
    'partial-absence',
)
SOURCE_PATHS = (
    'references/mechanisms.json',
    'references/recipes.json',
    'references/target-runtime-2.1.289.json',
    'references/official-docs.json',
    'docs/context-map.md',
    'docs/profile-design.md',
    'docs/mods-migration.md',
    'docs/target-runtime.md',
    'docs/context-retention.md',
    'docs/continuity-and-memory.md',
    'docs/context-cases.md',
    'docs/companion-context.md',
    'docs/compact-control.md',
    'docs/official-controls.md',
    'docs/request-observation.md',
    'context_lab/observations.py',
    'experiments/recipes/cases/owned-core.json',
    'experiments/recipes/cases/dynamic-state.json',
    'experiments/recipes/cases/compact-resume.json',
)


def _catalog():
    return mechanisms.load_catalog()


def _recipes():
    return recipes.load_catalog()['recipes']


class CatalogContracts(unittest.TestCase):
    def test_catalog_is_strict_exact_ordered_and_independent(self):
        first = _catalog()
        second = _catalog()
        self.assertEqual(first, second)
        self.assertEqual(first['schema'], 'cc-context-mechanisms/1')
        self.assertEqual(first['levels'], list(mechanisms.LEVELS))
        self.assertEqual(
            tuple(item['id'] for item in first['mechanisms']), EXPECTED_IDS)
        self.assertEqual(
            tuple(item['id'] for item in first['mechanisms']), mechanisms.MECHANISM_IDS)
        first['mechanisms'][0]['claims'][0]['statement'] = 'MUTATED'
        self.assertNotEqual(first, _catalog())
        first = _catalog()
        first['mechanisms'][0]['sources'][0]['locator']['heading'] = 'MUTATED'
        self.assertNotEqual(first, _catalog())

    def test_all_sources_are_fixed_local_existing_and_exactly_located(self):
        catalog = _catalog()
        source_ids = set()
        for mechanism in catalog['mechanisms']:
            for source in mechanism['sources']:
                with self.subTest(source=source['id']):
                    self.assertNotIn(source['id'], source_ids)
                    source_ids.add(source['id'])
                    self.assertIn(source['observed_on'], {
                        '2026-10-05', '2026-11-13'})
                    self.assertIn(source['kind'], mechanisms.SOURCE_KINDS)
                    self.assertTrue(source['locator'])
                    self.assertEqual(set(source), set(mechanisms.SOURCE_FIELDS))
                    self.assertTrue((ROOT / source['path']).is_file())
                    if source['kind'] in (
                            'authored_source', 'synthetic_fixture',
                            'public_source_pin'):
                        self.assertRegex(source['revision'], r'^[0-9a-f]{40}$')
        self.assertIn('34bc41ae80c0f5f2047b1cc272dd1663d4569a9c',
                      {s['revision'] for m in catalog['mechanisms']
                       for s in m['sources']})
        self.assertIn('@anthropic-ai/claude-code-darwin-arm64@2.1.289',
                      {s['revision'] for m in catalog['mechanisms']
                       for s in m['sources']})

    def test_every_claim_and_source_is_used_and_levels_stay_bounded(self):
        for mechanism in _catalog()['mechanisms']:
            local_ids = {source['id'] for source in mechanism['sources']}
            referenced = set()
            for claim in mechanism['claims']:
                self.assertTrue(claim['source_ids'])
                self.assertTrue(claim['limits'])
                self.assertTrue(set(claim['source_ids']) <= local_ids)
                referenced.update(claim['source_ids'])
            self.assertEqual(referenced, local_ids)
            self.assertTrue(all(row['level'] in mechanisms.LEVELS
                                for row in mechanism['claims']))

    def test_recipe_bindings_cover_all_seven_exact_mechanism_ids(self):
        recipe_rows = _recipes()
        catalog = _catalog()
        self.assertTrue(
            mechanisms.validate_recipe_bindings(recipe_rows, catalog))
        bound = [
            item['id'] for recipe in recipe_rows for item in recipe['mechanisms']
        ]
        self.assertEqual(tuple(bound), EXPECTED_IDS)
        for recipe in recipe_rows:
            self.assertEqual(recipe['native_status'], 'NOT_ASSESSED')
            for item in recipe['mechanisms']:
                self.assertTrue(item['sources'])

    def test_reading_paths_and_decisive_evidence_have_independent_jobs(self):
        rows = _recipes()
        before = deepcopy(rows)
        registry = _catalog()
        rows[0]['mechanisms'][0]['sources'] = ['docs/official-controls.md']
        self.assertTrue(mechanisms.validate_recipe_bindings(rows, registry))
        projected = mechanisms.build_recipe_evidence(rows[0], registry)
        self.assertEqual(projected['projection']['sources'], mechanisms.build_recipe_evidence(before[0], registry)['projection']['sources'])
        self.assertEqual(rows[0]['mechanisms'][0]['sources'], ['docs/official-controls.md'])

    def test_unknown_missing_duplicate_and_orphan_bindings_are_rejected(self):
        recipe_rows = _recipes()
        catalog = _catalog()

        def rejected(label, mutations, reference=recipe_rows, registry=catalog):
            with self.subTest(label=label):
                changed = deepcopy(reference)
                mutations(changed)
                with self.assertRaises(ValueError):
                    mechanisms.validate_recipe_bindings(changed, registry)

        rejected(
            'unknown mechanism',
            lambda value: value[0]['mechanisms'][0].update(id='not-a-mechanism'))
        rejected(
            'missing mechanism',
            lambda value: value[2]['mechanisms'].pop())
        rejected(
            'duplicate mechanism',
            lambda value: value[1]['mechanisms'].__setitem__(
                1, deepcopy(value[1]['mechanisms'][0])))
        for recipe_index, recipe in enumerate(recipe_rows):
            for mechanism_index, mechanism in enumerate(recipe['mechanisms']):
                with self.subTest(mechanism=mechanism['id']):
                    changed = deepcopy(recipe_rows)
                    changed[recipe_index]['mechanisms'][mechanism_index]['id'] = 'unbound-mechanism'
                    with self.assertRaises(ValueError):
                        mechanisms.validate_recipe_bindings(changed, catalog)

    def test_recipe_catalog_loads_registry_without_cycles(self):
        self.assertEqual(
            tuple(row['id'] for row in recipes.load_catalog()['recipes']),
            recipes.RECIPE_IDS)
        expected = _catalog()
        with tempfile.TemporaryDirectory(prefix='mechanism-cycle-') as temp:
            broken = Path(temp)
            for relative in SOURCE_PATHS:
                target = broken / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            (broken / 'references/mechanisms.json').write_text(
                (ROOT / 'references/mechanisms.json').read_text(
                    encoding='utf-8').replace(
                        'docs/mods-migration.md', '../escape.md', 1),
                encoding='utf-8')
            with self.assertRaises(ValueError):
                recipes.load_catalog(broken)
        self.assertEqual(expected, _catalog())


class SourceNegativeContracts(unittest.TestCase):
    def mutate_catalog(self, mutator):
        with tempfile.TemporaryDirectory(prefix='mechanism-source-') as temp:
            root = Path(temp)
            for relative in SOURCE_PATHS:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            catalog = json.loads(
                (root / 'references/mechanisms.json').read_text(encoding='utf-8'))
            mutator(catalog, root)
            (root / 'references/mechanisms.json').write_text(
                json.dumps(catalog, ensure_ascii=False), encoding='utf-8')
            with self.assertRaises(ValueError):
                mechanisms.load_catalog(root)

    def test_missing_escaping_and_nonregular_sources_are_rejected(self):
        def missing(value, root):
            value['mechanisms'][0]['sources'][0]['path'] = 'docs/missing.md'

        def escaped(value, root):
            value['mechanisms'][0]['sources'][0]['path'] = '../outside.md'

        def absolute(value, root):
            value['mechanisms'][0]['sources'][0]['path'] = '/tmp/source.md'

        def backslash(value, root):
            value['mechanisms'][0]['sources'][0]['path'] = 'docs\\context-map.md'

        def windows(value, root):
            value['mechanisms'][0]['sources'][0]['path'] = 'C:/source.md'

        def unterminated(value, root):
            value['mechanisms'][0]['sources'][0]['path'] = 'docs/context-map.md/'

        for label, mutation in (
                ('missing', missing), ('escape', escaped),
                ('absolute', absolute), ('backslash', backslash),
                ('windows drive', windows), ('trailing slash', unterminated)):
            with self.subTest(label=label):
                self.mutate_catalog(mutation)

    def test_symbol_locators_parse_definitions_instead_of_matching_quotes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'source.py'
            path.write_text('sample = """\ndef pretend():\n    pass\n"""\n\nclass Real:\n    def method(self):\n        pass\n', encoding='utf-8')
            mechanisms._locator(path, {'kind':'python_symbol','symbol':'Real.method'}, 'test')
            for symbol in ('pretend', 'Missing.method', 'Real.missing'):
                with self.subTest(symbol=symbol), self.assertRaises(ValueError):
                    mechanisms._locator(path, {'kind':'python_symbol','symbol':symbol}, 'test')

    def test_markdown_code_fences_do_not_invent_headings(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'source.md'
            path.write_text('```md\n## Fake\n```\n~~~md\n## Also fake\n~~~\n## Real\n', encoding='utf-8')
            mechanisms._locator(path, {'kind':'markdown_heading','heading':'Real'}, 'test')
            for heading in ('Fake', 'Also fake'):
                with self.subTest(heading=heading), self.assertRaises(ValueError):
                    mechanisms._locator(path, {'kind':'markdown_heading','heading':heading}, 'test')

    def test_missing_and_malformed_locators_are_rejected(self):
        def absent_pointer(value, root):
            value['mechanisms'][3]['sources'][2]['locator'][
                'pointer'] = '/steps/999/capture'

        def malformed_pointer(value, root):
            value['mechanisms'][3]['sources'][2]['locator'][
                'pointer'] = '/steps/~2'

        def absent_heading(value, root):
            value['mechanisms'][0]['sources'][0]['locator'][
                'heading'] = 'not present'

        def absent_symbol(value, root):
            value['mechanisms'][6]['sources'][1]['locator'][
                'symbol'] = '_not_present'

        def unknown_locator(value, root):
            value['mechanisms'][0]['sources'][0]['locator'] = {
                'kind': 'line', 'value': 1}

        for label, mutation in (
                ('absent JSON pointer', absent_pointer),
                ('malformed JSON pointer', malformed_pointer),
                ('absent heading', absent_heading),
                ('absent Python symbol', absent_symbol),
                ('unknown locator kind', unknown_locator)):
            with self.subTest(label=label):
                self.mutate_catalog(mutation)

    def test_source_kind_level_and_revision_inflation_are_rejected(self):
        def documentation_to_composition(value, root):
            value['mechanisms'][5]['claims'][0]['level'] = (
                'historical_local_composition')

        def synthetic_to_official(value, root):
            value['mechanisms'][1]['claims'][2]['level'] = (
                'official_documentation')

        def short_revision(value, root):
            value['mechanisms'][0]['sources'][0]['revision'] = '34bc41a'

        def spaced_artifact(value, root):
            value['mechanisms'][0]['sources'][2]['revision'] = (
                '@anthropic-ai/claude-code@2.1.289 current')

        def future_date(value, root):
            value['mechanisms'][0]['sources'][0]['observed_on'] = '2026-13-99'

        def url_escape(value, root):
            value['mechanisms'][0]['sources'][0]['url'] = (
                'file:///private/source')

        def mismatched_pin(value, root):
            value['mechanisms'][0]['sources'][0]['revision'] = 'a' * 40

        def mismatched_artifact(value, root):
            value['mechanisms'][0]['sources'][2]['revision'] = '@anthropic-ai/claude-code-darwin-arm64@2.1.999'

        def mismatched_observation(value, root):
            value['mechanisms'][0]['sources'][2]['observed_on'] = '2026-11-13'

        def unpinned_artifact_report(value, root):
            value['mechanisms'][0]['sources'][2]['url'] = 'https://registry.npmjs.org/@anthropic-ai/claude-code-darwin-arm64/2.1.289'

        for label, mutation in (
                ('documentation as composition', documentation_to_composition),
                ('synthetic as official', synthetic_to_official),
                ('short Git revision', short_revision),
                ('spaced artifact revision', spaced_artifact),
                ('malformed date', future_date),
                ('non-HTTP URL', url_escape),
                ('Git pin disagrees with URL', mismatched_pin),
                ('artifact disagrees with report', mismatched_artifact),
                ('artifact date disagrees with report', mismatched_observation),
                ('artifact version URL does not pin observation report', unpinned_artifact_report)):
            with self.subTest(label=label):
                self.mutate_catalog(mutation)

        with self.assertRaises(ValueError):
            mechanisms.load_catalog(ROOT / 'docs')

    def test_unknown_duplicate_and_orphan_registry_records_are_rejected(self):
        def unknown_claim(value, root):
            value['mechanisms'][0]['claims'][0]['source_ids'].append(
                'unknown-source')

        def duplicate_source(value, root):
            source = deepcopy(value['mechanisms'][0]['sources'][0])
            value['mechanisms'][1]['sources'].append(source)

        def duplicate_claim_id(value, root):
            value['mechanisms'][1]['claims'][0]['id'] = (
                value['mechanisms'][0]['claims'][0]['id'])

        def orphan_source(value, root):
            source = deepcopy(value['mechanisms'][0]['sources'][0])
            source['id'] = 'unreferenced-source'
            value['mechanisms'][0]['sources'].append(source)

        def wrong_order(value, root):
            value['mechanisms'].reverse()

        def wrong_levels(value, root):
            value['levels'][-1] = 'complete'

        def unknown_field(value, root):
            value['mechanisms'][0]['claims'][0]['readiness'] = 'PASS'

        for label, mutation in (
                ('unknown source ID', unknown_claim),
                ('duplicate source ID', duplicate_source),
                ('duplicate claim ID', duplicate_claim_id),
                ('orphan source record', orphan_source),
                ('wrong mechanism order', wrong_order),
                ('unknown evidence level', wrong_levels),
                ('readiness field', unknown_field)):
            with self.subTest(label=label):
                self.mutate_catalog(mutation)

    def test_duplicate_json_keys_and_nonfinite_values_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='mechanism-json-') as temp:
            root = Path(temp)
            for relative in SOURCE_PATHS:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            path = root / 'references/mechanisms.json'
            original = path.read_text(encoding='utf-8')
            for payload in (
                    '{"schema":"cc-context-mechanisms/1",'
                    '"schema":"cc-context-mechanisms/1",'
                    '"levels":[],"mechanisms":[]}',
                    original.replace('"schema": "cc-context-mechanisms/1"',
                                     '"schema": NaN')):
                path.write_text(payload, encoding='utf-8')
                with self.assertRaises(ValueError):
                    mechanisms.load_catalog(root)


class ProjectionContracts(unittest.TestCase):
    def test_projection_has_exact_schema_and_canonical_strings(self):
        catalog = _catalog()
        for recipe in _recipes():
            with self.subTest(recipe=recipe['id']):
                result = mechanisms.build_recipe_evidence(
                    recipe, catalog=catalog)
                self.assertEqual(
                    set(result), {'projection', 'json', 'markdown'})
                projection = result['projection']
                self.assertEqual(
                    set(projection),
                    {'schema', 'recipe_id', 'mechanisms', 'sources', 'caveats'})
                self.assertEqual(
                    projection['schema'], 'cc-context-recipe-evidence/1')
                self.assertEqual(projection['recipe_id'], recipe['id'])
                self.assertEqual(
                    tuple(row['id'] for row in projection['mechanisms']),
                    tuple(row['id'] for row in recipe['mechanisms']))
                for mechanism in projection['mechanisms']:
                    self.assertEqual(
                        set(mechanism),
                        {'id', 'title', 'explanation', 'claims'})
                    for claim in mechanism['claims']:
                        self.assertEqual(
                            set(claim), set(mechanisms.CLAIM_FIELDS))
                        self.assertIn(claim['level'], mechanisms.LEVELS)
                for source in projection['sources']:
                    self.assertEqual(set(source), set(mechanisms.SOURCE_FIELDS))
                self.assertTrue(projection['caveats'])
                self.assertEqual(
                    result['json'],
                    json.dumps(projection, ensure_ascii=False, indent=2,
                               allow_nan=False) + '\n')
                self.assertIn(result['json'].strip(), result['markdown'])
                self.assertIn(
                    '# Recipe mechanism evidence · ' + recipe['id'],
                    result['markdown'])
                for term in (
                        projection['mechanisms'][0]['claims'][0]['id'],
                        projection['sources'][0]['revision'],
                        projection['sources'][0]['observed_on'],
                        projection['sources'][0]['locator']['kind']):
                    self.assertIn(term, result['markdown'])
                self.assertNotIn('readiness', projection)
                self.assertNotIn('verified', projection)
                self.assertNotIn('request_body', projection)
                self.assertEqual(
                    tuple(row['id'] for row in recipes.load_catalog()['recipes']),
                    recipes.RECIPE_IDS)

    def test_rendering_is_deterministic_exact_and_mutation_free(self):
        catalog = _catalog()
        recipe = _recipes()[2]
        before_catalog = deepcopy(catalog)
        before_recipe = deepcopy(recipe)
        first = mechanisms.build_recipe_evidence(recipe, catalog)
        second = mechanisms.build_recipe_evidence(recipe, catalog)
        self.assertEqual(first, second)
        self.assertEqual(catalog, before_catalog)
        self.assertEqual(recipe, before_recipe)
        first['projection']['mechanisms'][0]['title'] = 'MUTATED'
        first['projection']['sources'][0]['limits'].append('MUTATED')
        self.assertEqual(catalog, before_catalog)
        self.assertNotEqual(
            mechanisms.build_recipe_evidence(recipe, catalog),
            first)
        for marking in (
                'target_binary_local_composition',
                'historical_offline_check',
                'historical_target_types',
                'unassessed'):
            if marking in json.dumps(first['projection']):
                self.assertIn(marking, first['markdown'])

    def test_markdown_fences_survive_backticks_and_unknown_levels_verbatim(self):
        catalog = _catalog()
        recipe = _recipes()[0]
        target = next(
            claim for mechanism in catalog['mechanisms']
            for claim in mechanism['claims']
            if mechanism['id'] == 'owned-core-boundary')
        target['statement'] += ' ```literal``` '
        result = mechanisms.build_recipe_evidence(recipe, catalog)
        self.assertIn('````json', result['markdown'])
        self.assertIn('```literal```', result['markdown'])
        self.assertIn('`historical_local_composition`', result['markdown'])
        self.assertIn('`unassessed`', result['markdown'])

    def test_native_status_and_malformed_inputs_are_not_promoted(self):
        catalog = _catalog()
        recipe = deepcopy(_recipes()[0])
        recipe['native_status'] = 'PASS'
        with self.assertRaises(ValueError):
            mechanisms.build_recipe_evidence(recipe, catalog)
        with self.assertRaises(ValueError):
            mechanisms.build_recipe_evidence([], catalog)
        with self.assertRaises(ValueError):
            mechanisms.build_recipe_evidence(
                deepcopy(_recipes()[0]), catalog, ROOT / 'missing-root')
        self.assertFalse((ROOT / 'references/mechanisms.json').is_symlink())

    def test_history_is_retained_as_history_not_current_runtime_evidence(self):
        selected = {
            source['id']: source
            for recipe in _recipes()
            for source in mechanisms.build_recipe_evidence(recipe, _catalog())[
                'projection']['sources']
        }
        runtime = selected['owned-boundary-runtime']
        self.assertEqual(runtime['observed_on'], '2026-10-05')
        self.assertEqual(
            runtime['revision'], '@anthropic-ai/claude-code-darwin-arm64@2.1.289')
        projection = mechanisms.build_recipe_evidence(
            _recipes()[0], _catalog())['projection']
        claims = {
            claim['id']: claim
            for mechanism in projection['mechanisms']
            for claim in mechanism['claims']
        }
        self.assertEqual(
            claims['claim-core-2-1-289-composition']['level'],
            'historical_local_composition')
        self.assertEqual(
            claims['claim-core-2-1-289-composition']['level'], 'historical_local_composition')
        self.assertNotIn(
            'historical_local_composition', {
                claim['level'] for recipe in _recipes()
                for mechanism in mechanisms.build_recipe_evidence(
                    recipe, _catalog())['projection']['mechanisms']
                for claim in mechanism['claims']
                if recipe['id'] == 'compact-resume' and claim['id'].startswith(
                    'claim-resume')})


if __name__ == '__main__':
    unittest.main(verbosity=2)
