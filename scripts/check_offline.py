#!/usr/bin/env python3
"""Run the authored lab's offline checks; no CC binary, network, or models.

Does not execute upstream fixtures requiring third-party checkouts, runtime
probes, installers, request transport, or provider evaluation.
"""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    node = shutil.which('node')
    if not node:
        print('Offline checks require Node.js; no installation attempted.', file=sys.stderr)
        return 2
    checks = [
        ('CC recipe contracts', [sys.executable, 'scripts/test_recipes.py']),
        ('recipe integration and toolkit dispatch', [sys.executable, 'scripts/test_recipe_atlas.py']),
        ('question workflow and loaded materials', [node, '--test', 'scripts/test_journey_ui.cjs']),
        ('question workflow syntax', [node, '--check', 'workbench/journeys.js']),
        ('companion input and typed decision contracts', [sys.executable, 'experiments/companion-input/run_lab.py', '--check', '--no-run']),
        ('context study and CLI', [sys.executable, 'scripts/test_context_study.py']),
        ('shared private output policy', [sys.executable, 'scripts/test_io_policy.py']),
        ('explicit CC run importer', [sys.executable, 'scripts/test_cc_runs.py']),
        ('selected Atlas comparison pairs', [sys.executable, 'scripts/test_atlas_pairs.py']),
        ('CC run snapshots and Atlas', [sys.executable, 'scripts/test_cc_run_view.py']),
        ('CC run presenter', [node, '--test', 'scripts/test_run_ui.cjs']),
        ('Atlas projection', [sys.executable, 'scripts/test_build_context_atlas.py']),
        ('context case and CLI', [sys.executable, 'scripts/test_context_cases.py']),
        ('case Atlas integration', [sys.executable, 'scripts/test_context_case_atlas.py']),
        ('case presenter and fixed handoff', [node, '--test', 'scripts/test_case_ui.cjs']),
        ('request observation and CLI', [sys.executable, 'scripts/test_context_observations.py']),
        ('Atlas output safety and canonical values', [sys.executable, 'scripts/test_atlas_output_safety.py']),
        ('observation presenter and fixed handoff', [node, '--test', 'scripts/test_observation_ui.cjs']),
        ('study import and handoff', [node, '--test', 'scripts/test_study_ui.cjs']),
        ('candidate logic', [node, '--test', 'experiments/context-profile/tests/register.test.js']),
        ('portable daily quiet rules', [node, '--test', 'experiments/daily-quiet/tests/rules.test.mjs']),
        ('offline checker boundary', [sys.executable, 'scripts/test_check_context_profile.py']),
        ('request preparation only', [sys.executable, 'scripts/test_prepare_heartbeat_requests.py']),
        ('Atlas script syntax', [node, '--check', 'workbench/app.js']),
        ('study script syntax', [node, '--check', 'workbench/study.js']),
        ('case script syntax', [node, '--check', 'workbench/cases.js']),
        ('CC run script syntax', [node, '--check', 'workbench/runs.js']),
        ('observation script syntax', [node, '--check', 'workbench/observations.js']),
    ]
    for label, command in checks:
        print('\nChecking ' + label, flush=True)
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode:
            print('FAILED: ' + label, file=sys.stderr)
            return result.returncode if result.returncode > 0 else 1
    print('\nOffline checks passed. Runtime requests, model behavior, installation and delivery remain separate.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
