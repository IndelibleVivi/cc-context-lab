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


class RecipeAtlasTests(unittest.TestCase):
    def test_each_bundle_has_exact_case_and_declared_comparisons(self):
        for recipe in load_catalog()['recipes']:
            bundle = atlas.recipe_bundle(recipe['id'])
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
