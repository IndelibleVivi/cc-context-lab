#!/usr/bin/env python3
"""Contract checks for saved context studies, projections and the local CLI.

Only synthetic repository fixtures and temporary files under .cache are used.
No Claude binary, model, transport, live history or upstream checkout is read.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / 'experiments' / 'companion-input'
sys.path.insert(0, str(LAB))
import context_study as study

CLI = ROOT / 'scripts' / 'run_context_study.py'
FIXED = 'P1_fixed_interval'
HYBRID = 'P6_hybrid'
SELF = 'P4_self_scheduled_one_shots'


def plan():
    return dict(
        schema='cc-context-study/1', title='旧天气、纠正与经历承接',
        question='换成 fresh 后，旧天气与较早的 recall 在哪里？',
        preserve=['原话与 channel wrapper 保真', '内部结果只能在产生之后承接'],
        fixture=json.loads((LAB / 'fixtures' / 'common_scenario.json').read_text(encoding='utf-8')),
        baseline=dict(policy_id=FIXED, placement_id='PL_main_defer', history_mode='same'),
        candidate=dict(policy_id=FIXED, placement_id='PL_main_defer', history_mode='fresh'))


def source(report, side, source_id):
    return next(item for item in report[side]['observations']['sources'] if item['id'] == source_id)


def packet_at(report, side, seconds):
    return next(packet for packet in report[side]['observations']['packets']
                if packet['actual_start'] == seconds)


def exposure_at(report, side, source_id, seconds):
    wake_id = packet_at(report, side, seconds)['wake_id']
    return next(exposure for exposure in source(report, side, source_id)['exposures']
                if exposure['wake_id'] == wake_id)


class StudyContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = study.run_study(plan())

    def test_saved_snapshot_roundtrip_and_projection_do_not_mutate_inputs(self):
        original = plan()
        before = deepcopy(original)
        validated = study.validate_plan(original)
        self.assertEqual(validated, before)
        validated['fixture']['timeline'][0]['id'] = 'changed-copy'
        self.assertEqual(original, before)

        report = study.run_study(original)
        self.assertEqual(original, before)
        original['fixture']['timeline'][0]['id'] = 'changed-after-run'
        self.assertEqual(report['plan'], before)
        replay = study.run_study(json.loads(json.dumps(report['plan'], ensure_ascii=False)))
        for side in ('baseline', 'candidate'):
            self.assertEqual(replay[side], report[side])

        raw = deepcopy(report['plan']['fixture'])
        run = deepcopy(report['baseline']['run'])
        saved_raw, saved_run = deepcopy(raw), deepcopy(run)
        projected = study.project_run(raw, run)
        self.assertEqual(raw, saved_raw)
        self.assertEqual(run, saved_run)
        projected['sources'][0]['payload']['id'] = 'changed-projection'
        self.assertEqual(raw, saved_raw)
        self.assertEqual(run, saved_run)

    def test_malformed_plans_fail_with_value_error_without_input_mutation(self):
        cases = [
            ('schema', lambda p: p.update(schema='unknown')),
            ('unknown executable field', lambda p: p.update(command='never execute')),
            ('empty question', lambda p: p.update(question='  ')),
            ('array selection', lambda p: p['baseline'].update(policy_id=[FIXED])),
            ('unknown history', lambda p: p['candidate'].update(history_mode='__proto__')),
            ('unknown policy', lambda p: p['candidate'].update(policy_id='missing-policy')),
            ('duplicate source ID', lambda p: p['fixture']['timeline'].append(deepcopy(p['fixture']['timeline'][0]))),
            ('zero interval', lambda p: p['fixture']['policies'][0].update(interval_seconds=0)),
            ('array policy kind', lambda p: p['fixture']['policies'][0].update(kind=[])),
            ('array event type', lambda p: p['fixture']['timeline'][0].update(type=[])),
            ('array placement rule', lambda p: p['fixture']['placements'][0].update(rule=[])),
            ('object placement target', lambda p: p['fixture']['placements'][0].update(target={})),
        ]
        for label, corrupt in cases:
            with self.subTest(label=label):
                raw = plan()
                corrupt(raw)
                before = deepcopy(raw)
                with self.assertRaises(ValueError):
                    study.validate_plan(raw)
                self.assertEqual(raw, before)

    def test_expired_weather_exits_current_without_erasing_seen_history(self):
        report = self.report
        old = source(report, 'baseline', 'amb_weather_1')
        raw = next(event for event in report['plan']['fixture']['timeline'] if event['id'] == old['id'])
        self.assertEqual(old['payload'], raw)
        self.assertTrue(exposure_at(report, 'baseline', old['id'], 300)['current'])
        for side, seen_history in (('baseline', True), ('candidate', False)):
            exposure = exposure_at(report, side, old['id'], 2100)
            self.assertFalse(exposure['current'])
            self.assertEqual(exposure['history'], seen_history)
            self.assertTrue(exposure['excluded'])
            self.assertTrue(exposure_at(report, side, 'amb_env_2', 2100)['current'])
        self.assertEqual(report['evidence']['runtime_request'], 'NOT_RUN')
        self.assertEqual(report['evidence']['model_evaluation'], 'NOT_RUN')
        self.assertFalse(report['evidence']['external_delivery'])

    def test_corrected_recall_is_historical_and_new_body_is_current(self):
        report = self.report
        old = exposure_at(report, 'baseline', 'recall_1', 2100)
        self.assertFalse(old['current'])
        self.assertTrue(old['history'])
        self.assertTrue(old['excluded'])
        self.assertTrue(any('referenced_memory' in reason for reason in old['reasons']))
        self.assertFalse(exposure_at(report, 'candidate', 'recall_1', 2100)['history'])
        for side in ('baseline', 'candidate'):
            self.assertTrue(exposure_at(report, side, 'recall_2', 2100)['current'])
            current = packet_at(report, side, 2100)['current']
            recall = next(block['payload'] for block in current if block['channel'] == 'passive_recall')
            self.assertEqual(recall['id'], 'recall_2')
            self.assertIn('soy latte', recall['body'])

    def test_original_human_payload_and_actual_wrapper_both_survive_projection(self):
        report = self.report
        raw = next(event for event in report['plan']['fixture']['timeline'] if event['id'] == 'msg_1')
        for side in ('baseline', 'candidate'):
            self.assertEqual(source(report, side, 'msg_1')['payload'], raw)
            observed = next(block['payload'] for block in packet_at(report, side, 2100)['current']
                            if block['channel'] == 'human_message')
            actual = next(packet for packet in report[side]['run']['packets']
                          if packet['wake']['candidate_id'] == packet_at(report, side, 2100)['wake_id'])
            self.assertEqual(observed, actual['user_text_blocks'][0])
            self.assertEqual(observed['exact_user_text'], raw['body'])
            self.assertEqual(observed['wrapper']['sender'], raw['sender'])
            self.assertEqual(observed['wrapper']['channel'], raw['channel'])
            self.assertEqual(observed['wrapper']['reply_target'], raw['reply_target'])
            self.assertEqual(observed['wrapper']['attachment'], raw['attachment'])
            self.assertEqual(observed['wrapper']['sender_time'], '00:27:55')
            self.assertEqual(observed['wrapper']['received_at'], '00:28:00')

    def test_new_internal_result_is_after_input_then_available_to_later_turn(self):
        report = self.report
        for side in ('baseline', 'candidate'):
            producer = exposure_at(report, side, 'internal_plan_1', 2100)
            self.assertTrue(producer['produced_after_input'])
            self.assertFalse(producer['current'])
            self.assertFalse(producer['history'])
            packet = packet_at(report, side, 2100)
            self.assertEqual([block['id'] for block in packet['produced_after_input']], ['internal_plan_1'])
            self.assertNotIn('internal_plan_1', [block['payload']['id'] for block in packet['current']])
        later = exposure_at(report, 'baseline', 'internal_plan_1', 2400)
        self.assertTrue(later['current'])
        self.assertTrue(later['history'])
        prior = next(block['payload'] for block in packet_at(report, 'baseline', 2400)['current']
                     if block['channel'] == 'prior_internal_result')
        self.assertFalse(prior['delivered'])
        self.assertFalse(exposure_at(report, 'candidate', 'internal_plan_1', 2400)['current'])

    def test_shared_trigger_ids_keep_merge_and_cancellation_facts(self):
        raw = plan()
        raw['baseline']['placement_id'] = 'PL_main_skip'
        raw['candidate']['history_mode'] = 'same'
        report = study.run_study(raw)
        comparison = report['comparison']
        self.assertEqual(comparison['alignment'], 'shared_trigger_ids')
        self.assertEqual(report['changed_axes'], ['placement_id'])
        fixed6 = next(row for row in comparison['matched'] if row['trigger_id'] == 'fixed-6')
        self.assertEqual(fixed6['baseline']['outcome'], 'skipped')
        self.assertEqual(fixed6['candidate']['actual_start'], 2100)
        merged = fixed6['candidate']['coalesced_trigger_ids']
        self.assertGreater(len(merged), 1)
        matches = {row['trigger_id']: row for row in comparison['matched']}
        self.assertEqual({matches[cid]['candidate']['wake_id'] for cid in merged},
                         {fixed6['candidate']['wake_id']})

        raw['baseline'].update(policy_id=SELF, placement_id='PL_main_defer')
        raw['candidate'].update(policy_id=SELF, placement_id='PL_independent')
        report = study.run_study(raw)
        cancelled = next(row for row in report['comparison']['matched']
                         if row['trigger_id'] == 'sw_cancel_pending')
        self.assertEqual(cancelled['baseline']['outcome'], 'dropped')
        self.assertEqual(cancelled['baseline']['placement_reason'], 'cancelled_before_actual_start')
        self.assertEqual(cancelled['candidate']['outcome'], 'admitted')

    def test_cross_policy_compound_comparison_does_not_invent_pairings(self):
        raw = plan()
        raw['candidate'].update(policy_id=HYBRID, placement_id='PL_independent')
        report = study.run_study(raw)
        self.assertEqual(set(report['changed_axes']), {'policy_id', 'placement_id', 'history_mode'})
        self.assertEqual(report['comparison_kind'], 'compound')
        comparison = report['comparison']
        self.assertEqual(comparison['alignment'], 'cross_policy_not_compared')
        self.assertEqual(comparison['matched'], [])
        for side in ('baseline', 'candidate'):
            self.assertEqual(comparison['unmatched_' + side], sorted(
                report[side]['observations']['opportunities'], key=lambda row: row['trigger_id']))
        self.assertNotIn('winner', comparison)
        markdown = study.render_markdown(report)
        self.assertIn(raw['question'], markdown)
        self.assertIn(raw['preserve'][0], markdown)
        self.assertIn('cross_policy_not_compared', markdown)
        self.assertIn('MODEL NOT RUN', markdown)


class CliContracts(unittest.TestCase):
    def setUp(self):
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='context-study-test-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def write_plan(self, path):
        # Deliberately noncanonical spacing: preservation is byte-level, not
        # merely parse-equivalence after a hidden rewrite of the source file.
        text = json.dumps(plan(), ensure_ascii=False, separators=(',', ':')) + '  \n'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path.read_bytes()

    def run_cli(self, input_path, output_dir):
        return subprocess.run([sys.executable, str(CLI), str(input_path), '--out', str(output_dir)],
                              cwd=ROOT, capture_output=True, text=True, timeout=30)

    def test_cli_writes_complete_reports_and_preserves_in_place_plan(self):
        incoming = self.directory / 'incoming.json'
        original = self.write_plan(incoming)
        out = self.directory / 'out'
        result = self.run_cli(incoming, out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(incoming.read_bytes(), original)
        self.assertEqual({p.name for p in out.iterdir()}, {'plan.json', 'result.json', 'result.md'})
        report = json.loads((out / 'result.json').read_text(encoding='utf-8'))
        self.assertEqual(report['plan'], json.loads(original))
        self.assertEqual(json.loads((out / 'plan.json').read_text(encoding='utf-8')), report['plan'])
        self.assertIn('MODEL NOT RUN', (out / 'result.md').read_text(encoding='utf-8'))

        in_place = out / 'plan.json'
        original_in_place = self.write_plan(in_place)
        result = self.run_cli(in_place, out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(in_place.read_bytes(), original_in_place)
        self.assertEqual(json.loads((out / 'result.json').read_text(encoding='utf-8'))['plan'],
                         json.loads(original_in_place))

    def test_invalid_json_and_plan_do_not_create_output(self):
        for index, content in enumerate(('{"broken":', '{"number": NaN}',
                                         json.dumps(dict(plan(), command='not allowed')))):
            with self.subTest(index=index):
                incoming = self.directory / ('invalid-%d.json' % index)
                incoming.write_text(content, encoding='utf-8')
                out = self.directory / ('invalid-out-%d' % index)
                result = self.run_cli(incoming, out)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(out.exists())
                self.assertEqual(incoming.read_text(encoding='utf-8'), content)

    def test_result_path_aliases_are_rejected_without_clobbering_input(self):
        for filename in ('result.json', 'result.md'):
            with self.subTest(filename=filename):
                out = self.directory / filename.replace('.', '-')
                incoming = out / filename
                original = self.write_plan(incoming)
                result = self.run_cli(incoming, out)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(incoming.read_bytes(), original)
                self.assertEqual({p.name for p in out.iterdir()}, {filename})
                self.assertIn('aliases', result.stderr)

    def test_symlink_and_hardlink_aliases_are_rejected_before_writes(self):
        incoming = self.directory / 'incoming.json'
        original = self.write_plan(incoming)
        for kind in ('symlink', 'hardlink'):
            with self.subTest(kind=kind):
                out = self.directory / kind
                out.mkdir()
                target = out / 'result.json'
                if kind == 'symlink':
                    target.symlink_to(incoming)
                else:
                    os.link(incoming, target)
                result = self.run_cli(incoming, out)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(incoming.read_bytes(), original)
                self.assertEqual({p.name for p in out.iterdir()}, {'result.json'})

    def test_aliased_outputs_and_non_file_target_fail_before_writes(self):
        incoming = self.directory / 'incoming.json'
        self.write_plan(incoming)
        out = self.directory / 'aliased-outputs'
        out.mkdir()
        first, second = out / 'result.json', out / 'result.md'
        first.write_text('existing report', encoding='utf-8')
        os.link(first, second)
        result = self.run_cli(incoming, out)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(first.read_text(encoding='utf-8'), 'existing report')
        self.assertFalse((out / 'plan.json').exists())

        other = self.directory / 'non-file-target'
        (other / 'result.md').mkdir(parents=True)
        result = self.run_cli(incoming, other)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse((other / 'plan.json').exists())
        self.assertFalse((other / 'result.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
