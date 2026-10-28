#!/usr/bin/env python3
"""Project canonical research and synthetic engine results into a local viewer.

No upstream queries, CC binary, model calls or live configuration. Run from any
cwd; default output is the repo's ignored .cache/context-atlas directory.
"""
import argparse
from datetime import datetime
import json
import os
import subprocess
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments' / 'companion-input'))
import run_session as rs
import context_study as study
from context_lab import observations as request_observation
from context_lab import cases
from context_lab.case_demo import make_demo_case
from context_lab.artifacts import paths_alias, write_reports


def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def build_request_observations(capture_paths=(), normalized=None):
    """Project explicit local captures and synthetic demos; never discover logs."""
    captures = [] if normalized is None else list(normalized)
    if normalized is None:
        paths = list(capture_paths) or sorted((ROOT / 'experiments/request-observation/fixtures').glob('*.json'))
        captures = [request_observation.normalize_capture(request_observation.parse_capture_json(Path(path).read_text(encoding='utf-8')))
                    for path in paths]
    ids = [capture['capture_id'] for capture in captures]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate capture_id in observations')
    comparisons = {a['capture_id']: {b['capture_id']: request_observation.compare_observations(a, b)
                                    for b in captures} for a in captures}
    reports = {aid: {bid: request_observation.render_markdown(report) for bid, report in rows.items()}
               for aid, rows in comparisons.items()}
    # Browser Number cannot preserve arbitrary JSON integers. Keep canonical
    # serialized values for display, search and JSON downloads, never round-trip
    # original payloads through JSON.parse/JSON.stringify in the browser.
    def display(value):
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    json_reports = {aid: {bid: json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
                          for bid, report in rows.items()} for aid, rows in comparisons.items()}
    display_values = {aid: {bid: dict(
        sections=[{side: display(row[side]['value']) if row[side] else None
                   for side in ('baseline', 'candidate')} for row in report['sections']],
        bodies={side: dict(body=display(report[side]['request_body']),
                           parameters=display(report[side]['request_parameters']))
                for side in ('baseline', 'candidate')})
        for bid, report in rows.items()} for aid, rows in comparisons.items()}
    return dict(captures=captures, comparisons=comparisons, reports=reports,
                json_reports=json_reports, display_values=display_values)


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


def build_data(study_plan=None, capture_paths=(), case_plan=None):
    explicit_case = case_plan is not None
    if case_plan is None and study_plan is None and not capture_paths:
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
    return dict(schema='cc-context-atlas/2',
                generated_on=datetime.now(ZoneInfo('Asia/Singapore')).date().isoformat(),
                model=model, upstreams=upstreams,
                compatibility=read_json('references/context-profile-compatibility.json'),
                target_runtime=read_json('references/target-runtime-2.1.289.json'),
                study_plan=study_plan,
                request_observations=build_request_observations(capture_paths,
                    normalized=[step['observation'] for step in case_projection['report']['steps'] if step['observation']]
                    if case_projection else None),
                context_case=case_projection, open_case=explicit_case,
                open_observation=bool(capture_paths),
                scenarios=scenarios)


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
    args = ap.parse_args()
    try:
        if args.case and (args.study or args.capture):
            raise ValueError('--case owns its snapshots; do not combine with --study or --capture')
        if args.capture or args.case:
            try:
                relative = args.out.resolve().relative_to(ROOT)
            except ValueError:
                pass  # Outside the Git worktree is an appropriate private output.
            else:
                ignored = subprocess.run(['git', 'check-ignore', '--quiet', '--', str(relative)], cwd=ROOT)
                if ignored.returncode != 0:
                    raise ValueError('capture output inside the worktree must be Git-ignored; use .cache/ or an external directory')
        for source in ([args.study] if args.study else []) + args.capture + ([args.case] if args.case else []):
            outputs = [args.out / 'data.json'] + ([] if args.data_only else [args.out / 'index.html'])
            for target in outputs:
                if paths_alias(target, source):
                    raise ValueError('input aliases generated output: ' + target.name)
        plan = json.loads(args.study.read_text(encoding='utf-8')) if args.study else None
        case_plan = request_observation.parse_capture_json(args.case.read_text(encoding='utf-8')) if args.case else None
        data = build_data(plan, args.capture, case_plan)
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
