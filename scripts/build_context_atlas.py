#!/usr/bin/env python3
"""Project canonical research and synthetic engine results into a local viewer.

No upstream queries, CC binary, model calls or live configuration. Run from any
cwd; default output is the repo's ignored .cache/context-atlas directory.
"""
import argparse
from datetime import datetime
import json
import os
import shlex
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments' / 'companion-input'))
import run_session as rs
import context_study as study
from context_lab import observations as request_observation
from context_lab import cases, io_policy
from context_lab.cc_run_view import load_run, project_run
from context_lab.case_demo import make_demo_case
from context_lab.artifacts import paths_alias, write_reports


def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def _json(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)


def build_request_observations(capture_paths=(), normalized=None, pairs=(), prepared=()):
    """Store each observation once and compute only explicitly selected pairs.

    Export tokens reference canonical Python strings; the browser concatenates
    them without parsing or re-encoding original numbers. No JS evaluator.
    """
    captures = [] if normalized is None else list(normalized)
    if normalized is None:
        paths = list(capture_paths) or sorted((ROOT / 'experiments/request-observation/fixtures').glob('*.json'))
        captures = [request_observation.normalize_capture(request_observation.parse_capture_json(Path(path).read_text(encoding='utf-8')))
                    for path in paths]
    by_id = {capture['capture_id']: capture for capture in captures}
    if len(captures) != len(by_id):
        raise ValueError('duplicate capture_id in observations')
    selected = []
    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2 or any(not isinstance(i, str) for i in pair):
            raise ValueError('comparison pair must contain baseline and candidate capture IDs')
        pair = tuple(pair)
        if pair[0] == pair[1] or any(i not in by_id for i in pair) or pair in selected:
            raise ValueError('comparison pair is self, duplicate or has an unknown capture ID')
        selected.append(pair)
    cached = {(r['baseline']['capture_id'], r['candidate']['capture_id']): r for r in prepared}
    serializations, display_values, metadata = {}, {}, []
    for capture in captures:
        cid = capture['capture_id']
        # These fragments serve downloads and UI independently. In particular,
        # no pair contains another copy of a request body or section value.
        serializations[cid] = dict(json=_json(capture),
            sections={row['pointer']: _json(row) for row in capture['sections']},
            markdown=request_observation._single_markdown(capture))
        display_values[cid] = dict(body=_json(capture['request_body']),
            parameters=_json(capture['request_parameters']),
            sections={row['pointer']: row['value'] if isinstance(row['value'], str) else _json(row['value'])
                      for row in capture['sections']})
        metadata.append({**{k: v for k, v in capture.items()
                            if k not in ('request_body', 'request_parameters', 'sections')},
                         'sections': [{k: v for k, v in row.items() if k != 'value'} for row in capture['sections']]})
    comparisons = {}
    for aid, bid in selected:
        report = cached.get((aid, bid))
        if report is None:
            report = request_observation.compare_observations(by_id[aid], by_id[bid])
        summary = {k: v for k, v in report.items() if k not in ('baseline', 'candidate', 'sections')}
        rows, row_tokens = [], []
        for row in report['sections']:
            compact = {k: v for k, v in row.items() if k not in ('baseline', 'candidate')}
            row_token = ['{' + ','.join(_json(k) + ':' + _json(v) for k, v in compact.items())]
            for side, cid in (('baseline', aid), ('candidate', bid)):
                section = row[side]
                compact[side] = ({k: v for k, v in section.items() if k != 'value'} if section else None)
                row_token += [',' + _json(side) + ':', {'capture': cid, 'section': section['pointer']} if section else 'null']
            row_token.append('}')
            rows.append(compact)
            if row_tokens:
                row_tokens.append(',')
            row_tokens += row_token
        tokens = ['{' + ','.join(_json(k) + ':' + _json(v) for k, v in summary.items()),
                  ',"baseline":', {'capture': aid}, ',"candidate":', {'capture': bid}, ',"sections":['] + row_tokens + [']}\n']
        # Render the canonical comparison introduction, without repeating either
        # capture. Markdown bodies are stored once per capture above.
        markdown = request_observation.render_markdown(report)
        marker = '\n## Baseline\n'
        prefix = markdown[:markdown.index(marker) + len(marker)]
        comparisons.setdefault(aid, {})[bid] = dict(summary, baseline_id=aid, candidate_id=bid,
            sections=rows, export_tokens=tokens, markdown_prefix=prefix)
    return dict(captures=metadata, comparisons=comparisons, serializations=serializations,
                display_values=display_values, selected_pairs=[list(p) for p in selected])


def expand_observation_export(data, baseline_id, candidate_id=None):
    """Expand one selected export; used by CLI tests and mirrored by presenter."""
    serial = data['serializations']
    if candidate_id is None:
        return dict(json=serial[baseline_id]['json'] + '\n',
                    markdown='# 请求 context 结构观察\n\n' + serial[baseline_id]['markdown'] + '\n')
    report = data['comparisons'].get(baseline_id, {}).get(candidate_id)
    if report is None:
        raise ValueError('comparison not prepared')
    def expand(token):
        if isinstance(token, str):
            return token
        record = serial[token['capture']]
        return record['sections'][token['section']] if 'section' in token else record['json']
    return dict(json=''.join(expand(t) for t in report['export_tokens']),
                markdown=report['markdown_prefix'] + '\n' + serial[baseline_id]['markdown'] +
                         '\n\n## Candidate\n\n' + serial[candidate_id]['markdown'] + '\n')


def build_case_projection(manifest):
    report = cases.run_case(manifest, study_runner=study.run_study)
    dumps = lambda value: json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    display = dict(
        checks={c['id']: dict(expected=dumps(c['expected']), actual=dumps(c['actual'])) for c in report['checks']},
        steps={step['id']: dumps(step['observation']['request_body']) if step['observation'] else None
               for step in report['steps']})
    def browser_safe(value):
        if type(value) is int:
            return abs(value) <= 9007199254740991
        if isinstance(value, dict):
            return all(browser_safe(v) for v in value.values())
        if isinstance(value, list):
            return all(browser_safe(v) for v in value)
        return True
    return dict(report=report, case_json=dumps(report['case']), report_json=dumps(report),
                markdown=cases.render_markdown(report), display=display,
                study_browser_safe=browser_safe(report['case']['study_plan']),
                study_markdown=study.render_markdown(report['study']) if report['study'] else None)


def build_data(study_plan=None, capture_paths=(), case_plan=None, pairs=None, run_bundle=None):
    explicit_case = case_plan is not None
    if case_plan is None and study_plan is None and not capture_paths and run_bundle is None:
        case_plan = make_demo_case(read_json('experiments/companion-input/fixtures/common_scenario.json'))
    case_projection = build_case_projection(case_plan) if case_plan is not None else None
    if case_projection and case_projection['report']['study']:
        # Unsafe case plans remain canonical report data only: do not feed
        # wireStudy's bootstrap restore or its editable scenario registry.
        study_plan = (case_projection['report']['case']['study_plan']
                      if case_projection['study_browser_safe'] else None)
    model = read_json('workbench/model.json')
    catalog = read_json('references/upstreams.json')
    scenarios = []
    fixtures = [json.loads(path.read_text(encoding='utf-8'))
                for path in sorted((ROOT / 'experiments' / 'companion-input' / 'fixtures').glob('*.json'))]
    if study_plan is not None:
        study_plan = study.validate_plan(study_plan)
        # Replace the same named built-in fixture with the imported snapshot;
        # never silently run an old plan against today's local source data.
        fixtures = [f for f in fixtures if f['scenario_id'] != study_plan['fixture']['scenario_id']]
        fixtures.insert(0, study_plan['fixture'])
    for raw in fixtures:
        fx = rs.Fixture(raw)
        runs = {p['id']: {
            pl['id']: {mode: rs.run_comparison(fx, p['id'], pl['id'], mode)
                       for mode in ('same', 'fresh')}
            for pl in fx.placements} for p in fx.policies}
        observations = {pid: {plid: {mode: study.project_run(raw, run)
                                     for mode, run in modes.items()}
                              for plid, modes in placements.items()}
                        for pid, placements in runs.items()}
        scenarios.append(dict(id=fx.scenario_id, title=raw.get('title', fx.scenario_id),
                              description=fx.description,
                              duration_seconds=raw['duration_seconds'],
                              timeline=raw['timeline'],
                              candidates_by_policy={p['id']: rs.generate_candidates(fx,p) for p in fx.policies},
                              policies=fx.policies,
                              placements=fx.placements, runs=runs,
                              fixture=raw, observations=observations))
    upstreams = [dict(repo=r['repo'], url=r['url'], revision=r['revision'],
                      observed_on=r.get('retrieved_on', catalog['checked_on']),
                      role=r.get('role', ''), coverage=r.get('coverage', ''),
                      runtime_verified=r.get('runtime_verified', False),
                      newer_tip=r.get('fetched_unread_tip')) for r in catalog['repositories']]
    run_projection = project_run(run_bundle[0], run_bundle[3]) if run_bundle else None
    normalized = ([step['observation'] for step in case_projection['report']['steps'] if step['observation']]
                  if case_projection else
                  [request_observation.normalize_capture(c) for c in run_bundle[1]] if run_bundle else None)
    prepared = [c['comparison'] for c in case_projection['report']['comparisons'] if c['comparison']] if case_projection else []
    selected = pairs if pairs is not None else list(dict.fromkeys(
        (r['baseline']['capture_id'], r['candidate']['capture_id']) for r in prepared))
    observations = build_request_observations(capture_paths, normalized=normalized, pairs=selected, prepared=prepared)
    if run_projection:
        observations['run_evidence_json'] = run_projection['run_json']
        observations['run_markdown'] = run_projection['evidence_markdown']
    return dict(schema='cc-context-atlas/3',
                generated_on=datetime.now(ZoneInfo('Asia/Singapore')).date().isoformat(),
                model=model, upstreams=upstreams,
                compatibility=read_json('references/context-profile-compatibility.json'),
                target_runtime=read_json('references/target-runtime-2.1.289.json'),
                study_plan=study_plan, request_observations=observations,
                cc_run=run_projection, open_run=bool(run_bundle),
                context_case=case_projection, open_case=explicit_case,
                open_observation=bool(capture_paths), scenarios=scenarios)



def compose_html(data):
    html = (ROOT / 'workbench' / 'index.html').read_text(encoding='utf-8')
    # JSON script content must not terminate its enclosing tag. Data remains
    # data: the UI renders source/user text using textContent or escaping.
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    parts = {'<!-- ATLAS_DATA -->': '<script id="atlas-data" type="application/json">' + payload + '</script>',
             '<!-- ATLAS_STYLE -->': '<style>' + (ROOT / 'workbench' / 'style.css').read_text(encoding='utf-8') + '</style>',
             '<!-- ATLAS_SCRIPT -->': '<script>' + (ROOT / 'workbench' / 'app.js').read_text(encoding='utf-8') + '</script>'}
    parts['<!-- ATLAS_STUDY_SCRIPT -->'] = '<script>' + (ROOT / 'workbench' / 'study.js').read_text(encoding='utf-8') + '</script>'
    parts['<!-- ATLAS_CASE_SCRIPT -->'] = '<script>' + (ROOT / 'workbench/cases.js').read_text(encoding='utf-8') + '</script>'
    parts['<!-- ATLAS_OBSERVATION_SCRIPT -->'] = '<script>' + (ROOT / 'workbench' / 'observations.js').read_text(encoding='utf-8') + '</script>'
    parts['<!-- ATLAS_RUN_SCRIPT -->'] = '<script>' + (ROOT / 'workbench/runs.js').read_text(encoding='utf-8') + '</script>'
    for marker, replacement in parts.items():
        if html.count(marker) != 1:
            raise ValueError('Expected one template marker: ' + marker)
        html = html.replace(marker, replacement)
    return html


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=ROOT / '.cache' / 'context-atlas')
    ap.add_argument('--data-only', action='store_true', help='project data without composing the UI')
    ap.add_argument('--study', type=Path, help='open a saved study using its embedded synthetic fixture snapshot')
    ap.add_argument('--capture', type=Path, action='append', default=[],
                    help='project only these explicit local capture JSON files (repeatable); output must stay private')
    ap.add_argument('--case', type=Path, help='open a self-contained harness-context-case/1; exclusive with --study/--capture')
    ap.add_argument('--run', type=Path, help='open one explicit imported run sidecar or frozen cc-run-snapshot/1')
    ap.add_argument('--pair', nargs=2, action='append', default=[], metavar=('BASELINE', 'CANDIDATE'),
                    help='prepare one directed comparison (repeatable); no implicit all-pairs')
    ap.add_argument('--pairs', type=Path, help='JSON array of [baseline, candidate] capture ID pairs')
    args = ap.parse_args()
    try:
        if args.run and (args.case or args.study or args.capture):
            raise ValueError('--run owns its selected captures; do not combine with --case/--study/--capture')
        if args.case and (args.study or args.capture):
            raise ValueError('--case owns its snapshots; do not combine with --study or --capture')
        outputs = [args.out / 'data.json'] + ([] if args.data_only else [args.out / 'index.html'])
        io_policy.ensure_private_output(args.out, ROOT, targets=outputs)
        for source in ([args.study] if args.study else []) + args.capture + ([args.case] if args.case else []) + ([args.pairs] if args.pairs else []) + ([args.run] if args.run else []):
            outputs = [args.out / 'data.json'] + ([] if args.data_only else [args.out / 'index.html'])
            for target in outputs:
                if paths_alias(target, source):
                    raise ValueError('input aliases generated output: ' + target.name)
        plan = json.loads(args.study.read_text(encoding='utf-8')) if args.study else None
        case_plan = request_observation.parse_capture_json(args.case.read_text(encoding='utf-8')) if args.case else None
        pairs = args.pair + (request_observation.parse_capture_json(args.pairs.read_text(encoding='utf-8')) if args.pairs else [])
        run_bundle = load_run(args.run) if args.run else None
        if run_bundle:
            for source in run_bundle[2]:
                for target in outputs:
                    if paths_alias(target, source):
                        raise ValueError('input aliases generated output: ' + target.name)
        data = build_data(plan, args.capture, case_plan, pairs=pairs if args.pair or args.pairs else None, run_bundle=run_bundle)
        rebuild = ['python3', 'scripts/build_context_atlas.py']
        if args.run:
            rebuild += ['--run', str(args.run)]
        elif args.case:
            rebuild += ['--case', str(args.case)]
        elif data.get('context_case'):
            rebuild += ['--case', 'context-case.json']
        else:
            if args.study:
                rebuild += ['--study', str(args.study)]
            for capture in args.capture:
                rebuild += ['--capture', str(capture)]
        data.setdefault('request_observations', {})['rebuild_command'] = shlex.join(rebuild + ['--pairs', 'comparison-pairs.json', '--out', str(args.out)])
        data['repo_base'] = os.path.relpath(ROOT, args.out.resolve()).replace(os.sep, '/')
        # Render everything before touching old artifacts; write_reports encodes
        # all content and atomically replaces each file without following links.
        contents = [(args.out / 'data.json', json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')]
        if not args.data_only:
            contents.append((args.out / 'index.html', compose_html(data)))
        write_reports(contents, args.out)
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        ap.error(str(exc))
    print(json.dumps({'output': str(args.out), 'html': not args.data_only,
                      'capabilities': len(data['model']['capabilities']),
                      'upstreams': len(data['upstreams']),
                      'synthetic_scenarios': len(data['scenarios'])}, ensure_ascii=False))

if __name__ == '__main__':
    main()
