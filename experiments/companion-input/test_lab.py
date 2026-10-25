#!/usr/bin/env python3
"""Fixture-derived expectations for placement, input provenance and reports."""
import copy
import json
from pathlib import Path
import unittest
import render
import run_lab
import run_session as rs

ROOT = Path(__file__).parent
FIXED = 'P1_fixed_interval'
HYBRID = 'P6_hybrid'
SELF = 'P4_self_scheduled_one_shots'


def fixture(name='common_scenario.json', extra=()):
    raw = rs.load_json(str(ROOT / 'fixtures' / name))
    raw['timeline'].extend(copy.deepcopy(extra))
    return rs.Fixture(raw)


def run(fx, policy=FIXED, placement='main_defer', mode='same'):
    return rs.run_comparison(fx, policy, 'PL_' + placement, mode)


def ids(blocks):
    return [b['id'] for b in blocks]


def at(report, seconds):
    return next(p for p in report['packets'] if p['wake']['actual_start'] == rs.format_time(seconds))


class ContractChecks(unittest.TestCase):
    def test_ui_only_environment_and_human_previews_never_become_input_or_history(self):
        fx = fixture(extra=[
            {'id':'ui_ambient','type':'ambient','t':1,'observed_at':1,'expires_at':9999,
             'text':'UI-only weather preview','ui_only':True},
            {'id':'ui_human','type':'human_message','t':1,'channel':'preview','sender':'fixture',
             'sender_time':1,'body':'UI-only message preview','ui_only':True},
        ])
        # Even explicit read-only/carryover selection must not turn a preview
        # into delivered model input. The archive retains the original data.
        fx.placements[2]['read_only_main_snapshots'].append('ui_human')
        fx.self_wakes['sw_afternoon']['carryover'].extend(['ui_ambient','ui_human'])
        for placement in ('main_defer','independent'):
            for mode in ('same','fresh'):
                report = run(fx, HYBRID, placement, mode)
                for packet in report['packets']:
                    for field in ('fresh_ambient_blocks','user_text_blocks','carried_history_or_carryover'):
                        self.assertFalse({'ui_ambient','ui_human'} & set(ids(packet[field])))
                exclusions = {e['id'] for p in report['packets'] for e in p['excluded']
                              if e['reason'] == 'ui_only:not_submitted'}
                self.assertTrue({'ui_ambient','ui_human'} <= exclusions)
        self.assertEqual(fx.by_id['ui_human']['body'],'UI-only message preview')

    def test_fixed_cadence_comes_from_interval(self):
        fx = fixture()
        cs = rs.generate_candidates(fx, fx.policies[0])
        self.assertEqual([c['trigger_time'] for c in cs], list(range(0, 4201, 300)))

    def test_turn_gap_has_three_distinct_outcomes(self):
        fx = fixture()
        self.assertFalse(fx.in_busy(1800))
        self.assertTrue(fx.in_chat(1800))
        skip, defer, indep = [run(fx, placement=p) for p in ('main_skip','main_defer','independent')]
        self.assertIn('fixed-6', skip['audit']['skipped_ids'])
        self.assertIn('fixed-6', at(defer, 2100)['wake']['coalesced_trigger_ids'])
        self.assertEqual(at(indep, 1800)['execution_target'], 'independent')
        self.assertFalse(at(indep, 1800)['wake']['turn_busy_at_trigger'])
        self.assertTrue(at(indep, 1800)['wake']['chat_active_at_trigger'])

    def test_no_main_start_during_chat_or_busy(self):
        fx = fixture()
        for policy in fx.policies:
            for placement in ('main_skip', 'main_defer'):
                for mode in ('same', 'fresh'):
                    for w in run(fx, policy['id'], placement, mode)['wakes']:
                        self.assertFalse(fx.in_chat(w['actual_start']))
                        self.assertFalse(fx.in_busy(w['actual_start'], 'main'))

    def test_multiple_chat_windows_resolve_locally_and_recheck_busy(self):
        raw=fixture().raw
        raw['timeline']=[{'id':'chat-a','type':'chat_interval','t':0,'end':100},
                         {'id':'chat-b','type':'chat_interval','t':200,'end':400},
                         {'id':'busy','type':'busy_interval','t':90,'end':220}]
        fx=rs.Fixture(raw)
        cs=[rs._cand('a','timer','external_timer',50,['a']),
            rs._cand('b','timer','external_timer',250,['b'])]
        placed=rs.place_candidates(fx,fx.placements[1],cs)
        self.assertEqual([w['actual_start'] for w in rs.admit(fx,placed)['admitted']],[400])
        # Without the crossing turn, the first chat must not wait for chat-b.
        raw['timeline']=raw['timeline'][:2]
        fx=rs.Fixture(raw)
        ws=rs.admit(fx,rs.place_candidates(fx,fx.placements[1],cs))['admitted']
        self.assertEqual([w['actual_start'] for w in ws],[100,400])

    def test_main_skip_rechecks_chat_after_turn_deferral(self):
        raw=fixture().raw
        raw['timeline']=[{'id':'turn','type':'busy_interval','t':0,'end':150},
                         {'id':'chat','type':'chat_interval','t':100,'end':200}]
        fx=rs.Fixture(raw)
        p=rs.place_candidates(fx,fx.placements[0],[rs._cand('c','timer','external_timer',50,['c'])])
        self.assertEqual(ids(p['skipped']),['c'])
        self.assertEqual(rs.admit(fx,p)['admitted'],[])

    def test_cancel_after_due_before_actual_start_removes_only_that_member(self):
        fx=fixture()
        r=run(fx,HYBRID)
        self.assertEqual(r['audit']['dropped_reasons']['sw_cancel_pending'],'cancelled_before_actual_start')
        b=at(r,2100)
        self.assertNotIn('sw_cancel_pending',b['wake']['coalesced_trigger_ids'])
        self.assertNotIn('self_wake_plan:sw_cancel_pending',b['wake']['scheduled_reasons'])
        self.assertNotIn('sw_cancel_pending',r['audit']['consumed_self_wake_ids'])
        self.assertTrue(b['wake']['coalesced_trigger_ids'])
        # The same plan can execute before cancellation in an independent session.
        self.assertIn('sw_cancel_pending',run(fx,SELF,'independent')['audit']['consumed_self_wake_ids'])

    def test_cancel_only_pending_group_produces_no_wake(self):
        fx=fixture()
        r=run(fx,SELF)
        self.assertNotIn(2100,[w['actual_start'] for w in r['wakes']])
        self.assertEqual(r['audit']['consumed_self_wake_ids'],['sw_reflect','sw_afternoon'])
        self.assertEqual(r['audit']['dropped_reasons']['sw_late'],'cancelled_before_actual_start')
        self.assertEqual(r['audit']['dropped_reasons']['sw_orphan'],'after_run_end')

    def test_stop_ends_deferred_and_future_wakes(self):
        raw=fixture().raw
        next(o for o in raw['timeline'] if o['type']=='run_end')['t']=2000
        r=run(rs.Fixture(raw))
        self.assertTrue(all(w['actual_start']<2000 for w in r['wakes']))
        self.assertEqual(r['audit']['dropped_reasons']['fixed-3'],'after_run_end')

    def test_skipped_self_wake_is_not_consumed(self):
        r=run(fixture(),SELF,'main_skip')
        self.assertIn('sw_cancel_pending',r['audit']['skipped_ids'])
        self.assertNotIn('sw_cancel_pending',r['audit']['consumed_self_wake_ids'])

    def test_independent_busy_coalesces_and_never_writes_main_ledger(self):
        fx=fixture(extra=[{'id':'more-busy','type':'busy_interval','t':1500,'end':1900,'session':'independent'}])
        r=run(fx,placement='independent')
        b=at(r,1900)
        self.assertEqual(set(b['wake']['coalesced_trigger_ids']),{'fixed-5','fixed-6'})
        self.assertEqual(r['audit']['session_ledger_ids']['main'],[])
        self.assertTrue(r['audit']['session_ledger_ids']['independent'])
        self.assertTrue(all(p['session_identity'].startswith('independent:') for p in r['packets']))

    def test_actual_start_reselects_weather_correction_and_human(self):
        b=at(run(fixture()),2100)
        self.assertEqual(ids(b['memory_items']),['mem_corr_2'])
        self.assertEqual(ids(b['passive_recall_blocks']),['recall_2'])
        self.assertIn('soy latte',b['passive_recall_blocks'][0]['body'])
        self.assertIn('amb_env_2',ids(b['fresh_ambient_blocks']))
        self.assertNotIn('amb_weather_1',ids(b['fresh_ambient_blocks']))
        self.assertIn('msg_1',ids(b['user_text_blocks']))
        self.assertEqual(b['placement']['rule'],'main_defer')

    def test_corrected_recall_removed_from_current_but_preserved_in_seen_history(self):
        fx=fixture()
        b=at(run(fx),2100)
        self.assertNotIn('recall_1',ids(b['passive_recall_blocks']))
        old=next(c for c in b['carried_history_or_carryover'] if c['id']=='recall_1')
        self.assertEqual(old['body'],fx.by_id['recall_1']['body'])
        self.assertIn('referenced_memory',next(e['reason'] for e in b['excluded'] if e['id']=='recall_1'))
        self.assertNotIn('recall_1',ids(at(run(fx,mode='fresh'),2100)['carried_history_or_carryover']))

    def test_existing_source_is_not_automatically_seen_history(self):
        first=run(fixture(),SELF)['packets'][0]
        self.assertEqual(first['carried_history_or_carryover'],[])
        self.assertEqual(first['wake']['candidate_id'],'sw_reflect')

    def test_expired_ambient_archive_is_not_current(self):
        fx=fixture()
        p=at(run(fx),2700)
        self.assertNotIn('amb_weather_1',ids(p['fresh_ambient_blocks']))
        self.assertIn('amb_weather_1',ids(p['carried_history_or_carryover']))
        self.assertEqual(fx.by_id['amb_weather_1']['text'],'Weather at coarse home area: 21C, light rain, wind 9km/h (synthetic).')

    def test_no_future_or_unselected_main_snapshot_in_either_history_mode(self):
        fx=fixture()
        for mode in ('same','fresh'):
            r=run(fx,placement='independent',mode=mode)
            self.assertEqual(at(r,0)['user_text_blocks'],[])
            self.assertNotIn('msg_1',ids(at(r,0)['carried_history_or_carryover']))
            h=at(r,1800)['user_text_blocks'][0]
            self.assertEqual(h['access'],'read_only_main_snapshot')
        fx.placements[2]['read_only_main_snapshots']=[]
        for mode in ('same','fresh'):
            r=run(fx,HYBRID,'independent',mode)
            self.assertFalse(any(p['user_text_blocks'] for p in r['packets']))
            self.assertFalse(any('msg_1' in ids(p['carried_history_or_carryover']) for p in r['packets']))

    def test_internal_result_appears_after_producing_turn_only(self):
        fx=fixture()
        same=run(fx)
        producer=at(same,2100)
        self.assertEqual(producer['internal_result_blocks'],[])
        self.assertEqual(ids(producer['scripted_produced_results']),['internal_plan_1'])
        self.assertEqual(ids(at(same,2400)['internal_result_blocks']),['internal_plan_1'])
        self.assertFalse(at(same,2400)['internal_result_blocks'][0]['delivered'])
        fresh=run(fx,mode='fresh')
        self.assertEqual(at(fresh,2400)['internal_result_blocks'],[])

    def test_fresh_internal_requires_explicit_available_carryover(self):
        fx=fixture()
        r=run(fx,SELF,mode='fresh')
        self.assertEqual(at(r,2200)['internal_result_blocks'],[])
        self.assertEqual(ids(at(r,2400)['internal_result_blocks']),['internal_plan_1'])
        self.assertEqual(ids(at(r,2400)['carried_history_or_carryover']),['internal_plan_1'])
        fx.self_wakes['sw_afternoon']['carryover']=[]
        self.assertEqual(at(run(fx,SELF,mode='fresh'),2400)['internal_result_blocks'],[])

    def test_unproduced_carryover_is_audited_not_invented(self):
        fx=fixture()
        fx.self_wakes['sw_reflect']['carryover']=['internal_plan_1']
        p=at(run(fx,SELF,mode='fresh'),2200)
        self.assertEqual(p['carried_history_or_carryover'],[])
        self.assertIn('internal_plan_1',ids(p['excluded']))

    def test_ui_only_never_in_current_recall_or_history(self):
        for mode in ('same','fresh'):
            r=run(fixture(),mode=mode)
            p=r['packets'][-1]
            self.assertNotIn('mem_ui',ids(p['memory_items']))
            self.assertNotIn('recall_ui',ids(p['passive_recall_blocks']))
            self.assertNotIn('mem_ui',ids(p['carried_history_or_carryover']))
            self.assertIn('ui_only',next(e['reason'] for e in p['excluded'] if e['id']=='mem_ui'))

    def test_modes_preserve_schedule_and_current_sources_but_change_history(self):
        fx=fixture()
        a,b=run(fx),run(fx,mode='fresh')
        self.assertEqual(a['wakes'],b['wakes'])
        for pa,pb in zip(a['packets'],b['packets']):
            for field in ('fresh_ambient_blocks','memory_items','user_text_blocks','passive_recall_blocks'):
                self.assertEqual(pa[field],pb[field])
        self.assertEqual(len({p['session_identity'] for p in a['packets']}),1)
        self.assertEqual(len({p['session_identity'] for p in b['packets']}),len(b['packets']))
        self.assertNotEqual(a['packets'][-1]['carried_history_or_carryover'],b['packets'][-1]['carried_history_or_carryover'])

    def test_jitter_is_listed_and_seconds_survive_rendering(self):
        fx=fixture()
        cs=rs.generate_candidates(fx,fx.policies[1])
        self.assertEqual([c['trigger_time'] for c in cs[:4]],[37,248,688,886])
        self.assertEqual(rs.format_time(37),'00:00:37')
        self.assertEqual(run(fx,fx.policies[1]['id']),run(fx,fx.policies[1]['id']))

    def test_idle_observes_a_full_window_and_events_do_not_self_trigger(self):
        fx=fixture('quiet_and_fresh_session.json')
        idle=rs.generate_candidates(fx,fx.policies[4])
        self.assertEqual([c['trigger_time'] for c in idle],[1800])
        events=rs.generate_candidates(fx,fx.policies[2])
        self.assertFalse(any(300<c['trigger_time']<2000 for c in events))
        self.assertFalse(any('internal_q1' in c['id'] for c in events))

    def test_unknown_delivery_survives_coalescing_without_success_claim(self):
        r=run(fixture(),HYBRID)
        p=at(r,2400)
        exact=next(o for o in p['scripted_outcomes'] if o['trigger']=='sw_afternoon')
        self.assertEqual(exact['external_delivery'],'unknown')
        self.assertNotIn('"delivered": true',json.dumps(r))

    def test_export_contains_full_payload_provenance_and_source_archive(self):
        fx=fixture()
        base,placements=run_lab.run_fixture(fx)
        blob=render.render_json(fx,base,placements)
        d=json.loads(blob)
        p=d['base_comparison'][FIXED]['same']['packets'][3]
        self.assertEqual(p['user_text_blocks'][0]['exact_user_text'],fx.by_id['msg_1']['body'])
        self.assertEqual(p['user_text_blocks'][0]['wrapper']['sender_time'],'00:27:55')
        self.assertEqual(p['user_text_blocks'][0]['origin'],'human_channel_message')
        self.assertIn('soy latte',p['passive_recall_blocks'][0]['body'])
        self.assertIn('observed_at',p['fresh_ambient_blocks'][0])
        self.assertIn('amb_weather_1',ids(d['source_archive']))
        md=render.render_markdown(fx,base,placements)
        self.assertIn('00:30:00 | 00:35:00 | main',md)
        self.assertIn(fx.by_id['recall_2']['body'],md)
        self.assertIn(fx.by_id['msg_1']['body'],md)

if __name__=='__main__':
    unittest.main(verbosity=2)
