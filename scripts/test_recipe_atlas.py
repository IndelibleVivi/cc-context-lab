#!/usr/bin/env python3
"""Recipe integration uses the canonical case engine and protects explicit inputs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import build_context_atlas as atlas
from context_lab.recipes import load_catalog, load_recipe_case
from context_lab.mechanisms import build_recipe_evidence
import build_mechanism_evidence as handbook


class RecipeAtlasTests(unittest.TestCase):
    def test_document_navigation_tracks_nested_output_root(self):
        data = atlas.build_data(recipe_id='owned-core')
        data['repo_base'] = '../../..'
        html = atlas.compose_html(data)
        self.assertIn('href="../../../docs/handbook/index.md"', html)
        self.assertIn('href="../../../docs/current-state.md"', html)
        self.assertNotIn('href="../../docs/', html)

    def test_each_bundle_has_exact_case_and_declared_comparisons(self):
        for recipe in load_catalog()['recipes']:
            bundle = atlas.recipe_bundle(recipe['id'])
            self.assertEqual(bundle['mechanism_evidence'], build_recipe_evidence(recipe))
            self.assertEqual(json.loads(bundle['context_case']['case_json']), load_recipe_case(recipe['id']))
            report = bundle['context_case']['report']
            projected = bundle['request_observations']
            self.assertEqual(len(projected['selected_pairs']), len(report['comparisons']))
            for pair in projected['selected_pairs']:
                exported = atlas.expand_observation_export(projected, *pair)
                self.assertEqual(json.loads(exported['json']), next(r['comparison'] for r in report['comparisons'] if r['comparison']['baseline']['capture_id'] == pair[0] and r['comparison']['candidate']['capture_id'] == pair[1]))

    def test_explicit_recipe_owns_case_and_other_input_is_not_merged(self):
        data = atlas.build_data(recipe_id='dynamic-state')
        self.assertEqual(data['context_case']['report']['case'], load_recipe_case('dynamic-state'))
        self.assertEqual(data['active_recipe_id'], 'dynamic-state')
        capture = atlas.ROOT/'experiments/request-observation/fixtures/anthropic-a.json'
        explicit = atlas.build_data(capture_paths=[capture])
        self.assertIsNone(explicit['context_case'])
        self.assertIsNone(explicit['active_recipe_id'])
        self.assertEqual(len(explicit['request_observations']['captures']), 1)
        self.assertEqual(set(explicit['recipe_examples']), {r['id'] for r in load_catalog()['recipes']})
        for bundle in explicit['recipe_examples'].values():
            self.assertNotIn('request_body', bundle['mechanism_evidence']['projection'])

    def test_evidence_cli_uses_canonical_strings_and_rejects_unknown_recipe(self):
        for recipe in load_catalog()['recipes']:
            evidence = build_recipe_evidence(recipe)
            for output_format, key in [('json', 'json'), ('markdown', 'markdown')]:
                result = subprocess.run([sys.executable, '-m', 'context_lab', 'evidence', '--recipe', recipe['id'], '--format', output_format], cwd=atlas.ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, evidence[key])
        result = subprocess.run([sys.executable, '-m', 'context_lab', 'evidence', '--recipe', '__proto__'], cwd=atlas.ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_handbook_projection_is_current_and_check_cannot_repair_stale_output(self):
        self.assertEqual(handbook.HANDBOOK_PATH.read_text(encoding='utf-8'), handbook.render_handbook_evidence())
        with tempfile.TemporaryDirectory() as temp:
            original = handbook.HANDBOOK_PATH
            target = Path(temp) / 'evidence.md'
            target.write_text('KEEP STALE', encoding='utf-8')
            try:
                handbook.HANDBOOK_PATH = target
                self.assertEqual(handbook.main(['--check']), 1)
                self.assertEqual(target.read_text(encoding='utf-8'), 'KEEP STALE')
            finally:
                handbook.HANDBOOK_PATH = original

    def test_dispatch_and_cli_conflict_keep_existing_output(self):
        result = subprocess.run([sys.executable,'-m','context_lab','recipes'], cwd=atlas.ROOT, capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(result.stdout.splitlines()),3)
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'index.html';target.write_text('KEEP')
            result=subprocess.run([sys.executable,'-m','context_lab','workbench','--recipe','owned-core','--case','missing.json','--out',temp],cwd=atlas.ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertIn('--recipe owns',result.stderr)
            self.assertEqual(target.read_text(),'KEEP')

if __name__=='__main__':
    unittest.main()
