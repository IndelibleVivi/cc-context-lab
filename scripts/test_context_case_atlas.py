#!/usr/bin/env python3
"""Case → canonical engines → Atlas integration, using synthetic local data only."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import build_context_atlas as atlas

ROOT = Path(__file__).resolve().parents[1]


def demo():
    return atlas.make_demo_case(atlas.read_json('experiments/companion-input/fixtures/common_scenario.json'))


def missing_case():
    return dict(schema='harness-context-case/1', case_id='missing', title='Missing evidence', question='Where is the input?',
                requirements=[dict(id='r',text='Input exists',level='request_structure')], study_plan=None,
                steps=[dict(id='s',label='Declared step without capture',capture=None)], comparisons=[],
                checks=[dict(id='c',requirement_id='r',step_id='s',pointer='/input',operator='absent',expected=None)])


class CaseAtlasIntegration(unittest.TestCase):
    def test_explicit_case_is_same_canonical_report_as_cli_and_owns_only_its_captures(self):
        case=demo()
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);incoming=base/'incoming.json';incoming.write_text(json.dumps(case,ensure_ascii=False))
            out=base/'out'
            result=subprocess.run([sys.executable,str(ROOT/'scripts/run_context_case.py'),str(incoming),'--out',str(out)],capture_output=True,text=True)
            self.assertEqual(result.returncode,1,result.stderr)
            data=atlas.build_data(case_plan=case);projection=data['context_case']
            self.assertEqual(projection['report_json'],(out/'report.json').read_text())
            self.assertEqual(projection['markdown'],(out/'report.md').read_text())
            self.assertEqual(json.loads(projection['case_json']),case)
            self.assertTrue(data['open_case']);self.assertFalse(data['open_observation'])
            self.assertEqual([o['capture_id'] for o in data['request_observations']['captures']],
                             [s['capture']['capture_id'] for s in case['steps'] if s['capture']])
            self.assertEqual(data['study_plan'],case['study_plan'])
            self.assertEqual(projection['report']['study'],atlas.study.run_study(case['study_plan']))

    def test_missing_capture_case_never_falls_back_to_default_demos_or_passes_absence(self):
        data=atlas.build_data(case_plan=missing_case())
        self.assertEqual(data['request_observations']['captures'],[])
        self.assertEqual(data['context_case']['report']['checks'][0]['status'],'NOT_ASSESSED')
        self.assertEqual(data['context_case']['report']['requirements'][0]['status'],'NOT_ASSESSED')
        self.assertIsNone(data['study_plan'])

    def test_big_integer_display_export_and_html_escaping_are_canonical(self):
        case=demo();step=next(s for s in case['steps'] if s['capture'])
        exact=9007199254740993
        step['capture']['body']['exact']=exact
        step['capture']['body']['literal']='</script><script>SYNTHETIC_DO_NOT_EXECUTE</script>'
        req=next(r for r in case['requirements'] if r['level']=='request_structure')
        case['checks'].append(dict(id='exact-integer',requirement_id=req['id'],step_id=step['id'],pointer='/exact',operator='equals',expected=exact))
        data=atlas.build_data(case_plan=case);projection=data['context_case'];html=atlas.compose_html(data)
        self.assertEqual(projection['display']['checks']['exact-integer']['actual'],'9007199254740993\n')
        self.assertIn('9007199254740993',projection['display']['steps'][step['id']])
        self.assertEqual(json.loads(projection['report_json'])['checks'][-1]['actual'],exact)
        self.assertNotIn('</script><script>SYNTHETIC',html)
        self.assertIn('ATLAS_CASE_SCRIPT', (ROOT/'workbench/index.html').read_text())
        self.assertNotIn('<!-- ATLAS_CASE_SCRIPT -->',html)

    def test_unsafe_study_integer_blocks_browser_restore_without_changing_saved_case(self):
        case=demo();case['study_plan']['fixture']['shared']['synthetic_integer']=9007199254740993
        projection=atlas.build_case_projection(case)
        self.assertFalse(projection['study_browser_safe'])
        self.assertEqual(json.loads(projection['case_json'])['study_plan']['fixture']['shared']['synthetic_integer'],9007199254740993)
        data=atlas.build_data(case_plan=case)
        self.assertIsNone(data['study_plan'], 'unsafe case must not reach wireStudy bootstrap')
        self.assertTrue(all('synthetic_integer' not in s['fixture']['shared'] for s in data['scenarios']),
                        'unsafe case fixture must not enter editable scenario registry')

    def test_independent_study_and_capture_paths_do_not_silently_attach_example_case(self):
        data=atlas.build_data(study_plan=demo()['study_plan'])
        self.assertIsNone(data['context_case']);self.assertFalse(data['open_case'])
        data=atlas.build_data(capture_paths=[ROOT/'experiments/request-observation/fixtures/responses-a.json'])
        self.assertIsNone(data['context_case']);self.assertTrue(data['open_observation'])
        self.assertEqual([o['capture_id'] for o in data['request_observations']['captures']],['synthetic-responses-a'])

    def test_case_flag_cannot_bypass_private_output_or_mix_input_owners(self):
        with tempfile.TemporaryDirectory() as directory:
            incoming=Path(directory)/'case.json';incoming.write_text(json.dumps(missing_case()))
            nonignored=ROOT/'synthetic-case-output-must-not-exist'
            self.assertFalse(nonignored.exists())
            for extra in ([],['--data-only'],['--study',str(incoming)],['--capture',str(incoming)]):
                with self.subTest(extra=extra):
                    result=subprocess.run([sys.executable,str(ROOT/'scripts/build_context_atlas.py'),'--case',str(incoming),'--out',str(nonignored),*extra],capture_output=True,text=True)
                    self.assertEqual(result.returncode,2,result.stderr);self.assertFalse(nonignored.exists())

    def test_invalid_case_and_input_output_alias_preserve_old_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);data=out/'data.json';index=out/'index.html';incoming=out/'case.json'
            data.write_text('KEEP DATA');index.write_text('KEEP HTML');incoming.write_text('{"schema":"wrong"}')
            for source in (incoming,data):
                result=subprocess.run([sys.executable,str(ROOT/'scripts/build_context_atlas.py'),'--case',str(source),'--out',str(out)],capture_output=True,text=True)
                self.assertEqual(result.returncode,2,result.stderr)
                self.assertEqual(data.read_text(),'KEEP DATA');self.assertEqual(index.read_text(),'KEEP HTML')
            # Strict duplicate keys fail before rendering or writes.
            incoming.write_text('{"schema":"harness-context-case/1","schema":"wrong"}')
            result=subprocess.run([sys.executable,str(ROOT/'scripts/build_context_atlas.py'),'--case',str(incoming),'--out',str(out)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2);self.assertEqual(data.read_text(),'KEEP DATA')


if __name__=='__main__':unittest.main()
