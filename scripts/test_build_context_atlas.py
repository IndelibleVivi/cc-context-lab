#!/usr/bin/env python3
"""Checks for the projection boundary, not a second copy of the wake engine."""
import json
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import build_context_atlas as atlas


class AtlasProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = atlas.build_data()

    def test_model_links_resolve_to_real_authorities(self):
        m = self.data['model']
        caps = {c['id'] for c in m['capabilities']}
        checks = {c['id'] for c in m['checks']}
        for c in m['capabilities']:
            self.assertTrue(set(c['check_ids']) <= checks)
            for e in c['evidence']:
                self.assertTrue((atlas.ROOT / e['source']).is_file(), e['source'])
        for e in m['edges']:
            self.assertTrue({e['from'], e['to']} <= caps)
        for intent in m['intents']:
            self.assertTrue(set(intent['capability_ids']) <= caps)
        for c in m['checks']:
            self.assertTrue((atlas.ROOT / c['source']).is_file())
            self.assertIn(c['category'], {'offline','local_probe','runtime_missing','read_only_network'})
            if c['id'] in ('actual-request', 'delivery-observation', 'runtime-handoff'):
                self.assertEqual(c['command'], '')

    def test_all_controls_have_engine_runs_including_gap_comparison(self):
        for s in self.data['scenarios']:
            self.assertEqual(set(s['runs']), {p['id'] for p in s['policies']})
            for placements in s['runs'].values():
                self.assertEqual(set(placements), {p['id'] for p in s['placements']})
                for modes in placements.values():
                    self.assertEqual(set(modes), {'same', 'fresh'})
        s = next(s for s in self.data['scenarios'] if s['id'] == 'common_rich_v1')
        runs = s['runs']['P1_fixed_interval']
        skip, defer, independent = [runs['PL_'+p]['same'] for p in ('main_skip','main_defer','independent')]
        self.assertIn('fixed-6', skip['audit']['skipped_ids'])
        self.assertEqual(next(c['trigger_time'] for c in s['candidates_by_policy']['P1_fixed_interval'] if c['id']=='fixed-6'), 1800)
        self.assertTrue(any(w['actual_start'] == 2100 and 'fixed-6' in w['coalesced_trigger_ids'] for w in defer['wakes']))
        self.assertTrue(any(w['actual_start'] == 1800 for w in independent['wakes']))
        self.assertEqual(independent['audit']['session_ledger_ids']['main'], [])

    def test_evidence_layers_and_read_pins_are_not_promoted(self):
        original = atlas.read_json('references/context-profile-compatibility.json')
        self.assertEqual(self.data['compatibility'], original)
        self.assertEqual(original['checks'][0]['request_behavior'], 'not_tested')
        self.assertEqual(original['checks'][0]['production_installation'], 'not_performed')
        self.assertEqual(self.data['target_runtime'], atlas.read_json('references/target-runtime-2.1.289.json'))
        source = atlas.read_json('references/upstreams.json')['repositories']
        self.assertEqual([(r['repo'],r['revision']) for r in self.data['upstreams']],
                         [(r['repo'],r['revision']) for r in source])

    def test_html_embeds_data_without_executable_source_text(self):
        data = dict(self.data, example='</script><script>globalThis.BAD=1</script>')
        html = atlas.compose_html(data)
        self.assertNotIn('<!-- ATLAS_', html)
        start = html.index('<script id="atlas-data" type="application/json">')
        body = html[start:].split('>',1)[1].split('</script>',1)[0]
        self.assertEqual(json.loads(body)['example'],data['example'])
        self.assertNotIn('<script>',body)
        self.assertNotIn('globalThis.BAD=1</script>',html)

    def test_study_observations_use_the_same_canonical_run_and_snapshot(self):
        for scenario in self.data['scenarios']:
            self.assertEqual(scenario['fixture']['scenario_id'], scenario['id'])
            for pid, placements in scenario['runs'].items():
                for plid, modes in placements.items():
                    for mode, run in modes.items():
                        obs = scenario['observations'][pid][plid][mode]
                        self.assertEqual(len(obs['packets']), len(run['packets']))
                        self.assertEqual(obs['schema'], 'cc-context-study-observations/1')
        s = self.data['scenarios'][0]
        run = s['runs']['P1_fixed_interval']['PL_main_defer']['same']
        obs = s['observations']['P1_fixed_interval']['PL_main_defer']['same']
        self.assertEqual(obs, atlas.study.project_run(s['fixture'], run))

    def test_saved_study_keeps_its_embedded_material_despite_same_scenario_name(self):
        fixture = deepcopy(self.data['scenarios'][0]['fixture'])
        fixture['description'] = 'Synthetic archived snapshot; different local contents.'
        plan = dict(schema='cc-context-study/1',title='Snapshot',question='Does the original input survive?',
                    preserve=['original input'], fixture=fixture,
                    baseline=dict(policy_id='P1_fixed_interval',placement_id='PL_main_defer',history_mode='same'),
                    candidate=dict(policy_id='P1_fixed_interval',placement_id='PL_main_defer',history_mode='fresh'))
        saved = atlas.build_data(plan)
        scenario = next(s for s in saved['scenarios'] if s['id'] == fixture['scenario_id'])
        self.assertEqual(scenario['fixture'], fixture)
        self.assertEqual(saved['study_plan'], plan)
        self.assertEqual(sum(s['id'] == fixture['scenario_id'] for s in saved['scenarios']),1)
        self.assertNotEqual(self.data['scenarios'][0]['fixture']['description'], fixture['description'])

    def test_builder_rejects_a_study_input_alias_before_overwriting_it(self):
        cache = atlas.ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as directory:
            incoming = Path(directory) / 'data.json'
            original = '{"kept":"source input"}\n'
            incoming.write_text(original, encoding='utf-8')
            result = subprocess.run([sys.executable, str(atlas.ROOT / 'scripts/build_context_atlas.py'),
                                     '--study', str(incoming), '--out', directory, '--data-only'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('input aliases', result.stderr)
            self.assertEqual(incoming.read_text(encoding='utf-8'), original)

if __name__ == '__main__':
    unittest.main(verbosity=2)
