"""Reproducible synthetic context studies over the canonical companion engine.

This module observes canonical results. It has no transport, scheduler, model,
configuration loader, or runtime side effects. A saved fixture is input data.
"""
from copy import deepcopy
import json

import run_session as rs

PLAN_SCHEMA = 'cc-context-study/1'
AXES = ('policy_id', 'placement_id', 'history_mode')
SOURCE_TYPES = {'ambient', 'memory', 'human_message', 'passive_recall', 'internal'}
EVENT_TYPES = SOURCE_TYPES | {'tick', 'busy_interval', 'chat_interval',
                             'ambient_expire', 'self_wake', 'cancel', 'run_end'}
CURRENT_CHANNELS = {
    'fresh_ambient_blocks': 'ambient', 'memory_items': 'memory',
    'user_text_blocks': 'human_message', 'passive_recall_blocks': 'passive_recall',
    'internal_result_blocks': 'prior_internal_result',
}


def _require(condition, field, message):
    if not condition:
        raise ValueError(field + ': ' + message)


def _text(value, field):
    _require(isinstance(value, str) and bool(value.strip()), field, 'expected nonempty string')


def _integer(value, field, minimum=0):
    _require(type(value) is int and value >= minimum, field,
             'expected integer >= ' + str(minimum))


def _strings(value, field):
    _require(isinstance(value, list) and all(isinstance(s, str) for s in value),
             field, 'expected string array')


def _records(items, field, nonempty=False):
    _require(isinstance(items, list) and (not nonempty or bool(items)), field, 'expected records')
    ids = set()
    for i, item in enumerate(items):
        label = '%s[%d]' % (field, i)
        _require(isinstance(item, dict), label, 'expected object')
        _text(item.get('id'), label + '.id')
        _require(item['id'] not in ids, label + '.id', 'duplicate ID')
        ids.add(item['id'])
    return {item['id']: item for item in items}


def validate_plan(plan):
    """Validate the executable fixture contract; return an independent snapshot."""
    fields = {'schema', 'title', 'question', 'preserve', 'fixture', 'baseline', 'candidate'}
    _require(isinstance(plan, dict) and set(plan) == fields, 'plan', 'unknown or missing fields')
    _require(plan['schema'] == PLAN_SCHEMA, 'schema', 'unsupported plan schema')
    for key in ('title', 'question'):
        _text(plan[key], key)
    _strings(plan['preserve'], 'preserve')
    try:
        json.dumps(plan, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('plan: not finite JSON data') from exc
    f = plan['fixture']
    _require(isinstance(f, dict), 'fixture', 'expected object')
    _text(f.get('scenario_id'), 'fixture.scenario_id')
    _integer(f.get('duration_seconds'), 'fixture.duration_seconds')
    _require(isinstance(f.get('shared'), dict), 'fixture.shared', 'expected object')
    _require(isinstance(f.get('outcomes'), list) and all(isinstance(o, dict) for o in f['outcomes']),
             'fixture.outcomes', 'expected object array')
    for i, outcome in enumerate(f['outcomes']):
        _text(outcome.get('trigger'), 'fixture.outcomes[%d].trigger' % i)
    policies = _records(f.get('policies'), 'fixture.policies', True)
    placements = _records(f.get('placements'), 'fixture.placements', True)
    events = _records(f.get('timeline'), 'fixture.timeline')
    for pid, p in policies.items():
        field = 'fixture.policies.' + pid
        _require(isinstance(p.get('kind'), str) and p['kind'] in {'fixed_interval', 'jittered_interval', 'event_driven',
                                  'self_wake', 'idle_window', 'hybrid'}, field, 'unknown policy kind')
        if p['kind'] in ('fixed_interval', 'jittered_interval', 'hybrid'):
            interval = p.get('interval_seconds', 300)
            _integer(interval, field + '.interval_seconds', 1)
            # A pasted plan must fail explicitly rather than expand billions of
            # periodic opportunities in a local offline process.
            _require(f['duration_seconds'] // interval <= 10000, field,
                     'more than 10000 periodic opportunities; narrow the fixture horizon')
        if p['kind'] == 'jittered_interval':
            offsets = p.get('jitter_offsets_seconds')
            _require(isinstance(offsets, list) and bool(offsets) and all(type(n) is int for n in offsets),
                     field + '.jitter_offsets_seconds', 'expected nonempty integer array')
        if p['kind'] == 'idle_window':
            _integer(p.get('idle_after_seconds', 600), field + '.idle_after_seconds')
        if 'events' in p:
            _strings(p['events'], field + '.events')
            _require(set(p['events']) <= EVENT_TYPES, field + '.events', 'unknown occurrence type')
    for eid, event in events.items():
        field = 'fixture.timeline.' + eid
        kind = event.get('type')
        _require(isinstance(kind, str) and kind in EVENT_TYPES, field + '.type', 'unknown occurrence type')
        _integer(event.get('t'), field + '.t')
        for key in ('observed_at', 'expires_at', 'planned_for', 'sender_time'):
            if event.get(key) is not None:
                _integer(event[key], field + '.' + key)
        for key in ('ui_only', 'disabled'):
            if key in event:
                _require(type(event[key]) is bool, field + '.' + key, 'expected boolean')
        if kind in ('busy_interval', 'chat_interval'):
            _integer(event.get('end'), field + '.end', event['t'])
        if kind in ('memory', 'ambient'):
            _require(isinstance(event.get('text', ''), str), field + '.text', 'expected text')
        if kind in ('human_message', 'passive_recall', 'internal'):
            _require(isinstance(event.get('body'), str), field + '.body', 'expected text')
        if kind == 'human_message':
            for key in ('channel', 'sender'):
                _text(event.get(key), field + '.' + key)
            _integer(event.get('sender_time'), field + '.sender_time')
        for key, target_type in (('corrects', 'memory'), ('source_memory_id', 'memory')):
            if event.get(key) is not None:
                target = events.get(event[key]) if isinstance(event[key], str) else None
                _require(target is not None and target.get('type') == target_type,
                         field + '.' + key, 'unknown or wrong-type source reference')
        if kind in ('cancel', 'ambient_expire'):
            target = events.get(event.get('target')) if isinstance(event.get('target'), str) else None
            _require(target is not None and target.get('type') == ('self_wake' if kind == 'cancel' else 'ambient'),
                     field + '.target', 'unknown or wrong-type target')
        if 'carryover' in event:
            _strings(event['carryover'], field + '.carryover')
            _require(set(event['carryover']) <= set(events), field + '.carryover', 'unknown source reference')
    _require(sum(e['type'] == 'run_end' for e in events.values()) <= 1,
             'fixture.timeline', 'at most one run_end is supported')
    for plid, p in placements.items():
        field = 'fixture.placements.' + plid
        _require(isinstance(p.get('rule'), str) and isinstance(p.get('target'), str) and (p['rule'], p['target']) in {
            ('main_skip', 'main'), ('main_defer', 'main'), ('independent', 'independent')},
            field, 'unsupported rule/target combination')
        refs = p.get('read_only_main_snapshots', [])
        _strings(refs, field + '.read_only_main_snapshots')
        _require(all(ref in events and events[ref]['type'] == 'human_message' for ref in refs),
                 field + '.read_only_main_snapshots', 'expected human source references')
    for side in ('baseline', 'candidate'):
        selection = plan[side]
        _require(isinstance(selection, dict) and set(selection) == set(AXES), side, 'unknown or missing fields')
        for key in AXES:
            _text(selection[key], side + '.' + key)
        _require(selection['policy_id'] in policies, side + '.policy_id', 'unknown policy')
        _require(selection['placement_id'] in placements, side + '.placement_id', 'unknown placement')
        _require(selection['history_mode'] in ('same', 'fresh'), side + '.history_mode', 'unknown history mode')
    fx = rs.Fixture(f)
    for policy in fx.policies:
        candidates = rs.generate_candidates(fx, policy)
        _require(len({c['id'] for c in candidates}) == len(candidates), 'fixture.policies.' + policy['id'],
                 'duplicate generated candidate identities')
    return deepcopy(plan)


def project_run(fixture, run):
    """Index actual canonical output, without deriving fresh source truth."""
    raw = fixture.raw if isinstance(fixture, rs.Fixture) else fixture
    fx = rs.Fixture(raw)
    selection = dict(policy_id=run['policy_id'], placement_id=run['placement_id'],
                     history_mode=run['session_mode'])
    sources = {e['id']: dict(id=e['id'], payload=deepcopy(e),
                           provenance=dict(scenario_id=fx.scenario_id, source_type=e['type'],
                                           fixture_time=e['t'], source_memory_id=e.get('source_memory_id'),
                                           corrects=e.get('corrects')),
                           exposures=[], produced_after_input=[])
               for e in raw['timeline'] if e['type'] in SOURCE_TYPES}
    packets = []
    wakes_by_id = {w['id']: w for w in run['wakes']}
    for packet in run['packets']:
        wake_id = packet['wake']['candidate_id']
        start = wakes_by_id[wake_id]['actual_start']
        current = [dict(channel=channel, payload=deepcopy(block))
                   for field, channel in CURRENT_CHANNELS.items() for block in packet[field]]
        history = deepcopy(packet['carried_history_or_carryover'])
        excluded = deepcopy(packet['excluded'])
        produced = deepcopy(packet['scripted_produced_results'])
        observations = dict(wake_id=wake_id, actual_start=start, actual_start_text=rs.format_time(start),
                            session_identity=packet['session_identity'], execution_target=packet['execution_target'],
                            current=current, history=history, excluded=excluded,
                            produced_after_input=produced,
                            scripted_outcomes=deepcopy(packet['scripted_outcomes']))
        packets.append(observations)
        for sid, source in sources.items():
            cur = [b for b in current if b['payload']['id'] == sid]
            hist = [b for b in history if b['id'] == sid]
            exc = [b for b in excluded if b['id'] == sid]
            post = [b for b in produced if b['id'] == sid]
            exposure = dict(wake_id=wake_id, actual_start=start, actual_start_text=rs.format_time(start),
                            current=bool(cur), history=bool(hist), excluded=bool(exc),
                            present=bool(cur or hist), produced_after_input=bool(post),
                            channels=[b['channel'] for b in cur],
                            reasons=[e['reason'] for e in packet['included'] if e['id'] == sid] +
                                    [e['reason'] for e in exc])
            source['exposures'].append(exposure)
            source['produced_after_input'].extend(dict(wake_id=wake_id, actual_start=start, payload=b) for b in post)
    policy = next(p for p in fx.policies if p['id'] == run['policy_id'])
    admitted = {c['id']: w for w in run['wakes'] for c in w['candidates']}
    opportunities = []
    for c in rs.generate_candidates(fx, policy):
        wake = admitted.get(c['id'])
        skipped = c['id'] in run['audit']['skipped_ids']
        opportunities.append(dict(
            trigger_id=c['id'], trigger_time=c['trigger_time'],
            owner_kind=c['owner_kind'], owner_detail=c['owner_detail'],
            outcome='admitted' if wake else ('skipped' if skipped else 'dropped'),
            wake_id=wake['id'] if wake else None, actual_start=wake['actual_start'] if wake else None,
            coalesced_trigger_ids=deepcopy(wake['coalesced_trigger_ids']) if wake else [],
            reasons=deepcopy(c['reasons']),
            placement_reason=wake['placement_reason'] if wake else
                run['audit']['skipped_reasons'].get(c['id'], run['audit']['dropped_reasons'].get(c['id']))))
    return dict(schema='cc-context-study-observations/1', selection=selection,
                summary=dict(wakes=len(packets), current_sources=sum(any(e['current'] for e in s['exposures']) for s in sources.values()),
                             historical_sources=sum(any(e['history'] for e in s['exposures']) for s in sources.values()),
                             skipped=len(run['audit']['skipped_ids']), dropped=len(run['audit']['dropped_ids'])),
                sources=list(sources.values()), packets=packets, opportunities=opportunities)


def compare_observations(baseline, candidate):
    """Compare observed traces; no winner, scoring or invented causal match."""
    same_policy = baseline['selection']['policy_id'] == candidate['selection']['policy_id']
    a = {o['trigger_id']: o for o in baseline['opportunities']}
    b = {o['trigger_id']: o for o in candidate['opportunities']}
    shared = sorted(set(a) & set(b)) if same_policy else []
    rows = [dict(trigger_id=key, baseline=a[key], candidate=b[key]) for key in shared]
    sa = {s['id']: s for s in baseline['sources']}
    sb = {s['id']: s for s in candidate['sources']}
    source_rows = [dict(id=key, payload=deepcopy((sa.get(key) or sb[key])['payload']),
                        provenance=deepcopy((sa.get(key) or sb[key])['provenance']),
                        baseline=sa.get(key, {}).get('exposures', []),
                        candidate=sb.get(key, {}).get('exposures', []),
                        changed=sa.get(key, {}).get('exposures', []) != sb.get(key, {}).get('exposures', []))
                   for key in sorted(set(sa) | set(sb))]
    return dict(alignment='shared_trigger_ids' if same_policy else 'cross_policy_not_compared',
                matched=rows, unmatched_baseline=[a[k] for k in sorted(set(a) - set(shared))],
                unmatched_candidate=[b[k] for k in sorted(set(b) - set(shared))], sources=source_rows,
                interpretation='Observed lab differences only; no quality ranking or single-factor causal claim.')


def run_study(plan):
    plan = validate_plan(plan)
    fx = rs.Fixture(plan['fixture'])
    report = dict(schema='cc-context-study-result/1', plan=plan,
                  evidence=dict(execution='OFFLINE_SYNTHETIC', model_evaluation='NOT_RUN',
                                runtime_request='NOT_RUN', installation='NOT_PERFORMED',
                                external_delivery=False, engine_source_snapshot='NOT_INCLUDED'),
                  changed_axes=[key for key in AXES if plan['baseline'][key] != plan['candidate'][key]])
    report['comparison_kind'] = 'compound' if len(report['changed_axes']) > 1 else (
        'single_axis' if report['changed_axes'] else 'identical_conditions')
    for side in ('baseline', 'candidate'):
        c = plan[side]
        run = rs.run_comparison(fx, c['policy_id'], c['placement_id'], c['history_mode'])
        report[side] = dict(selection=deepcopy(c), run=run, observations=project_run(fx, run))
    report['comparison'] = compare_observations(report['baseline']['observations'], report['candidate']['observations'])
    return report


def _json(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)


def render_markdown(report):
    plan = report['plan']
    lines = ['# ' + plan['title'], '', '> OFFLINE_SYNTHETIC · MODEL NOT RUN。不是实际 CC request 或模型评测。', '',
             '研究问题：' + plan['question'], '', '场景：' + plan['fixture']['scenario_id'], '',
             '比较类型：' + report['comparison_kind'], '',
             '变化轴：' + (', '.join(report['changed_axes']) or '无'), '',
             '多轴同时改变时不能单因果归因；次数、来源数或载荷大小不决定哪种相处更好。', '',
             '## 声明的保留条件（不自动判为通过）', '']
    lines.extend('- ' + s for s in plan['preserve'])
    lines.extend(['', '## 两组条件与实际观察', ''])
    for side in ('baseline', 'candidate'):
        lines.extend(['### ' + side, '', '```json', _json(dict(selection=report[side]['selection'],
                     summary=report[side]['observations']['summary'])), '```', ''])
    lines.extend(['## 按原始候选 identity 对齐', '',
                  '对齐方式：' + report['comparison']['alignment'], '',
                  '共享 policy 按 constituent trigger ID 对齐；合并成员可共用 wake，不按数组下标匹配。跨 policy 不造对应关系。', '',
                  '```json', _json({k:v for k,v in report['comparison'].items() if k != 'sources'}), '```', '',
                  '## 逐来源 current / history / excluded / 轮后产生', '',
                  'actual_start 是合成起点后的秒数。current 退出不表示历史或 archive 删除；结果只在产生之后承接。'])
    for source in report['comparison']['sources']:
        lines.extend(['', '### ' + source['id'], '', '轨迹' + ('不同' if source['changed'] else '相同'), '',
                      '```json', _json(source), '```'])
    lines.extend(['', '## 未验层级与重跑', '',
                  '真实 request、模型语义、scheduler、安装/激活和外部交付均未执行。保留条件需要研究者沿实际轨迹判断。',
                  'typed decision 仍为独立 shadow 实验，本比较没有按其意图重算 ledger。',
                  'plan.json 保存完整输入 snapshot；重跑使用当前引擎代码，不包含引擎源码，也不保证跨代码版本相同结果。', '',
                  '```sh', 'python3 scripts/run_context_study.py plan.json --out .cache/context-study', '```', '',
                  '完整来源、变换后的原话 wrapper 与每轮输入位于 result.json 的 plan/observations/run；原文不会被选择计数替代。'])
    return '\n'.join(lines) + '\n'
