#!/usr/bin/env python3
"""Companion input / heartbeat comparison lab (offline, deterministic).

Two independent axes:

* **trigger axis**  — six illustrative trigger policies (shared timeline);
* **placement axis** — three illustrative placement rules
  (``main_skip`` / ``main_defer`` / ``independent``).

Comparisons written to an ignored output dir (default ``.cache/companion-input``):

1. **Base** — the six policies under ``main_defer`` × two history modes
   (``same`` / ``fresh``).
2. **Placement** — a focused fixed/hybrid comparison across the three placement
   rules (not a full Cartesian product).

From the repo root:

    python3 experiments/companion-input/run_lab.py
    python3 experiments/companion-input/run_lab.py --fixtures experiments/companion-input/fixtures
    python3 experiments/companion-input/run_lab.py --out .cache/companion-input

There is no clock, sleep, daemon, HTTP, LLM or real message delivery.  See
README.md.  Exit codes: 0 = ran and wrote reports; 2 = fixture/CLI error.
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import run_session as rs  # noqa: E402
import render  # noqa: E402

DEFAULT_FIXTURES = os.path.join(_HERE, "fixtures")
DEFAULT_OUT = os.path.join(".cache", "companion-input")
MODES = ["same", "fresh"]
PLACEMENT_POLICIES = ["P1_fixed_interval", "P6_hybrid"]

def find_fixtures(path):
    if os.path.isdir(path):
        return [os.path.join(path, n) for n in sorted(os.listdir(path))
                if n.endswith(".json")]
    return [path]

def run_fixture(fx):
    """Base comparison: all policies under main_defer × both history modes."""
    main_defer = next(p for p in fx.placements if p["rule"] == "main_defer"
                      and p["target"] == "main")
    base = {}
    for policy in fx.policies:
        pid = policy["id"]
        base[pid] = {m: rs.run_comparison(fx, pid, main_defer["id"], m) for m in MODES}
    # Focused placement comparison: fixed/hybrid across all placement rules.
    placements = {}
    for pid in PLACEMENT_POLICIES:
        if not any(p["id"] == pid for p in fx.policies):
            continue
        placements[pid] = {}
        for pl in fx.placements:
            placements[pid][pl["id"]] = {
                m: rs.run_comparison(fx, pid, pl["id"], m) for m in MODES
            }
    return base, placements

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixtures", default=DEFAULT_FIXTURES)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true",
                    help="run the independent hand-expected contract checks and exit 0/1")
    ap.add_argument("--no-run", action="store_true",
                    help="with --check, skip writing reports")
    args = ap.parse_args(argv)

    if args.check:
        import subprocess
        checks = ["test_lab.py", "test_decision_schema.py", "test_decision_lab.py"]
        for name in checks:
            rc = subprocess.call([sys.executable, os.path.join(_HERE, name)],
                                 cwd=os.getcwd())
            if rc != 0:
                return rc
        if args.no_run:
            return 0

    paths = find_fixtures(args.fixtures)
    if not paths:
        sys.stderr.write("no fixture JSON found at %s\n" % args.fixtures)
        return 2

    os.makedirs(args.out, exist_ok=True)
    for path in paths:
        try:
            fx = rs.Fixture(rs.load_json(path))
        except Exception as exc:
            sys.stderr.write("failed to load fixture %s: %s\n" % (path, exc))
            return 2
        base, placements = run_fixture(fx)
        with open(os.path.join(args.out, "%s.json" % fx.scenario_id), "w",
                  encoding="utf-8") as fh:
            fh.write(render.render_json(fx, base, placements))
        with open(os.path.join(args.out, "%s.md" % fx.scenario_id), "w",
                  encoding="utf-8") as fh:
            fh.write(render.render_markdown(fx, base, placements))
        sys.stdout.write("wrote %s.json / %s.md\n" % (fx.scenario_id, fx.scenario_id))
    return 0

if __name__ == "__main__":
    sys.exit(main())
