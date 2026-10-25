#!/usr/bin/env python3
"""Typed heartbeat decision experiment: prepare + scripted replay.

Offline, pure standard library.  No HTTP, credentials, model call, scheduler or
message delivery.  Answers come from ``decision_cases.json`` and are labelled
``SCRIPTED_REPLAY``; this is NOT a model evaluation.

Examples (from the repo root):

    python3 experiments/companion-input/run_decisions.py --check
    python3 experiments/companion-input/run_decisions.py
    python3 experiments/companion-input/run_decisions.py --prepare-only
    python3 experiments/companion-input/run_decisions.py --out .cache/companion-input/decisions

The task shape (``heartbeat_activity`` + five options) is a repository-owned
contract, explicitly NOT any provider's wire body.

Exit codes: 0 = ran and wrote reports; 1 = a case expectation failed; 2 = CLI /
fixture error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import run_session as rs  # noqa: E402
import decision_schema as ds  # noqa: E402
import decision_engine as de  # noqa: E402

DEFAULT_FIXTURES = os.path.join(_HERE, "fixtures")
DEFAULT_CASES = os.path.join(_HERE, "decision_cases.json")
DEFAULT_OUT = os.path.join(".cache", "companion-input", "decisions")

MODE_LABEL = "SCRIPTED_REPLAY"


# ---------------------------------------------------------------------------
# Rules baseline (a comparison yardstick, NOT ground truth)
# ---------------------------------------------------------------------------

def rule_baseline(name, task):
    """A trivial deterministic 'policy' used only as a comparison baseline."""
    if name in (None, "none"):
        return None
    observed = task["observed_state"]
    if name == "always_remain_quiet":
        return "remain_quiet"
    if name == "contact_if_human_message_else_quiet":
        return "prepare_contact" if observed["human_messages"] else "remain_quiet"
    if name == "internal_if_ambient_fresh_else_quiet":
        return "internal_activity" if observed["fresh_ambient"] else "remain_quiet"
    return None


# ---------------------------------------------------------------------------
# Suite
# ---------------------------------------------------------------------------

def _find_task(tasks, candidate_id):
    for task in tasks:
        if task["candidate"]["wake_id"] == candidate_id:
            return task
        if candidate_id in task["candidate"]["coalesced_trigger_ids"]:
            return task
    return None


def run_case(fixtures_dir, case, prepare_only=False):
    selection = case["selection"]
    prepared = de.prepare(fixtures_dir, selection)
    tasks, audit = prepared["tasks"], prepared["audit"]
    candidate = case["candidate"]
    expect = {} if prepare_only else case.get("expect", {})

    record = {
        "case_id": case["id"],
        "mode": MODE_LABEL,
        "narrative": case.get("narrative", ""),
        "selection": selection,
        "candidate": candidate,
        "blocked": bool(expect.get("blocked")),
        "audit": audit,
        "rule_baseline": {
            "rule": case.get("rule_baseline"),
            "option": None,
            "note": "comparison baseline only; not ground truth",
        },
        "task": None,
        "replay": None,
        "violations": [],
    }
    violations = record["violations"]

    if prepare_only:
        task = _find_task(tasks, candidate)
        if task is None and candidate not in {b["id"] for b in audit["blocked_candidates"]}:
            raise ValueError("unknown candidate: %s" % candidate)
        record["task"] = task
        record["blocked"] = task is None
        return record

    if expect.get("blocked"):
        if _find_task(tasks, candidate) is not None:
            violations.append("blocked candidate produced a task")
        blocked_ids = {b["id"]: b for b in audit["blocked_candidates"]}
        if candidate not in blocked_ids:
            violations.append("blocked candidate missing from audit")
        elif blocked_ids[candidate]["reason"] != expect.get("blocked_reason"):
            violations.append("blocked reason mismatch: %s" % blocked_ids[candidate]["reason"])
        return record

    task = _find_task(tasks, candidate)
    if task is None:
        violations.append("expected a task for candidate %s but none was prepared" % candidate)
        return record
    record["task"] = task
    record["rule_baseline"]["option"] = rule_baseline(case.get("rule_baseline"), task)

    # Bind the synthetic answer to this task id + revision explicitly.  The
    # binding is the consume-entry contract; it is not a provider echo.
    bound_answer = dict(case["answer"])
    bound_answer.setdefault("task_id", task["task_id"])
    bound_answer.setdefault("state_revision", task["state_revision"])
    replay = de.consume(
        fixtures_dir, task, bound_answer, case["consume_time_s"],
        case.get("consume_overrides", ()),
    )
    record["bound_answer"] = bound_answer
    record["replay"] = replay

    # ---- expectation checks ------------------------------------------------
    if "gate_result" in expect and replay["gate"]["gate_result"] != expect["gate_result"]:
        violations.append("gate_result %s != %s"
                          % (replay["gate"]["gate_result"], expect["gate_result"]))
    if "released" in expect and expect["released"] is not None:
        if replay.get("released") != expect["released"]:
            violations.append("released %s != %s" % (replay.get("released"), expect["released"]))
    if expect.get("discard_reasons"):
        got = [replay.get("discard_reason")]
        if got != expect["discard_reasons"]:
            violations.append("discard_reason %s != %s" % (got, expect["discard_reasons"]))
    answer = replay.get("answer") or {}
    status = answer.get("status") if answer.get("classified", True) is not False else None
    if "status" in expect and expect["status"] is not None:
        if status != expect["status"]:
            violations.append("status %s != %s" % (status, expect["status"]))
    if expect.get("acceptable_options") is not None:
        # Any ok answer within one of the case's acceptable options passes.
        chosen = answer.get("option")
        if chosen not in expect["acceptable_options"]:
            violations.append("option %s not in acceptable %s"
                              % (chosen, expect["acceptable_options"]))
    if expect.get("option_is_none"):
        if answer.get("option") is not None:
            violations.append("expected option None, got %s" % answer.get("option"))
    if "error_kind" in expect and answer.get("error_kind") != expect["error_kind"]:
        violations.append("error_kind %s != %s"
                          % (answer.get("error_kind"), expect["error_kind"]))

    if expect.get("coalesced"):
        task_c = task["candidate"]
        if not task_c.get("coalesced"):
            violations.append("expected a coalesced task")
        if expect.get("coalesced_count") is not None:
            if len(task_c.get("constituents", [])) != expect["coalesced_count"]:
                violations.append("coalesced count %s != %s"
                                  % (len(task_c.get("constituents", [])),
                                     expect["coalesced_count"]))

    intent = replay.get("hypothetical_intent")
    if intent is not None:
        if intent["external_delivery"] is not False:
            violations.append("external_delivery must always be false")
        if expect.get("schedules_timer") is False and intent["schedules_timer"] is not False:
            violations.append("schedules_timer must be false")
        if "produces_draft_proposal" in expect:
            if intent["produces_draft_proposal"] != expect["produces_draft_proposal"]:
                violations.append("produces_draft_proposal mismatch")
        if "injection_boundary" in expect and intent["injection_boundary"] != expect["injection_boundary"]:
            violations.append("injection_boundary mismatch")

    if expect.get("confidence_retained"):
        if answer.get("confidence") is None:
            violations.append("expected confidence retained")
    if expect.get("probabilities_retained"):
        if not answer.get("probabilities"):
            violations.append("expected probabilities retained")

    return record


def run_suite(fixtures_dir, cases_path, prepare_only=False):
    data = rs.load_json(cases_path)
    records = [run_case(fixtures_dir, case, prepare_only=prepare_only) for case in data["cases"]]
    violations = [(r["case_id"], v) for r in records for v in r["violations"]]
    return data, records, violations


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _tasks_jsonl(records):
    """Export prepared tasks, de-duplicated by ``(task_id, state_revision)``.

    Several cases may select the same (fixture, policy, placement, history,
    wake) and therefore share one task_id.  Identical task_id+revision is
    emitted once.  The same task_id with a *different* revision is a genuine
    contradiction and is refused rather than silently overwritten.
    """
    lines: List[str] = []
    seen: Dict[str, str] = {}
    for record in records:
        task = record["task"]
        if task is None:
            continue
        task_id, revision = task["task_id"], task["state_revision"]
        if task_id in seen:
            if seen[task_id] != revision:
                raise ValueError(
                    "task_id %s reused with a different state_revision "
                    "(%s != %s); refusing to overwrite" % (task_id, seen[task_id], revision))
            continue
        seen[task_id] = revision
        lines.append(json.dumps(task, ensure_ascii=False, sort_keys=True))
    return "\n".join(lines) + ("\n" if lines else "")


def render_replay_json(data, records, violations):
    return json.dumps({
        "mode": MODE_LABEL,
        "model_evaluation": "NOT_RUN",
        "model_evaluation_note": (
            "SCRIPTED_REPLAY only: answers are synthetic fixture inputs, not "
            "model outputs. No model was called."
        ),
        "disclaimer": data.get("disclaimer", ""),
        "suite_id": data.get("suite_id"),
        "task_kind": data.get("task_kind"),
        "not_a_provider_wire_body": True,
        "option_set": data.get("option_set"),
        "violations": [{"case_id": c, "violation": v} for c, v in violations],
        "cases": records,
    }, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def render_replay_markdown(data, records, violations):
    L = []
    w = L.append
    w("# Typed heartbeat decision — %s" % MODE_LABEL)
    w("")
    w("> **%s** — synthetic answers from `decision_cases.json`. NOT a model "
      "evaluation, NOT real Claude Code behaviour. No HTTP, credentials, model "
      "call, scheduler or message delivery. The `heartbeat_activity` task is a "
      "repository-owned contract, not any provider's wire body. **MODEL NOT "
      "RUN.**" % MODE_LABEL)
    w("")
    w("Suite `%s`; option set: %s"
      % (data.get("suite_id"), ", ".join("`%s`" % o for o in data.get("option_set", []))))
    w("")
    if violations:
        w("## Expectation violations (%d)" % len(violations))
        w("")
        for case_id, violation in violations:
            w("- `%s`: %s" % (case_id, violation))
        w("")
    else:
        w("All case expectations satisfied.")
        w("")
    for record in records:
        w("## `%s`" % record["case_id"])
        w("")
        w("%s" % record["narrative"])
        w("")
        w("- selection: fixture=`%s` policy=`%s` placement=`%s` history=`%s`"
          % (record["selection"]["fixture"], record["selection"]["policy"],
             record["selection"]["placement"], record["selection"]["history"]))
        if record["blocked"]:
            blocked = {b["id"]: b for b in record["audit"]["blocked_candidates"]}
            info = blocked.get(record["candidate"], {})
            w("- **blocked candidate** `%s` (fate=%s, reason=%s) → no decision task; "
              "audited only."
              % (record["candidate"], info.get("fate"), info.get("reason")))
            w("")
            continue
        task = record["task"]
        candidate = task["candidate"]
        w("- task `%s`" % task["task_id"])
        w("- candidate wake `%s` owner=`%s/%s` target=`%s` start=%s (deferred=%s, coalesced=%s)"
          % (candidate["wake_id"], task["trigger_owner"]["kind"],
             task["trigger_owner"]["detail"], task["execution_target"],
             task["actual_start"], task["placement_context"]["deferred"],
             candidate["coalesced"]))
        if candidate["coalesced"]:
            w("- coalesced constituents (provenance preserved, one task): %s"
              % ", ".join("`%s`" % c["id"] for c in candidate["constituents"]))
        w("- state revision: `%s`" % task["state_revision"])
        observed = task["observed_state"]
        w("- observed evidence: ambient=%s memory=%s human=%s recall=%s "
          "prior_internal=%s history=%s"
          % (len(observed["fresh_ambient"]), len(observed["memory"]),
             len(observed["human_messages"]), len(observed["passive_recall"]),
             len(observed["prior_internal_results"]),
             len(observed["historical_material"])))
        w("- question `%s` options: %s"
          % (task["task_kind"], ", ".join("`%s`" % o["option"] for o in task["question"]["options"])))
        base = record["rule_baseline"]
        w("- rule baseline `%s` → `%s` (comparison only, not ground truth)"
          % (base["rule"], base["option"]))
        replay = record["replay"]
        answer = replay.get("answer") or {}
        w("- answer status=`%s`%s%s (SCRIPTED)"
          % (answer.get("status", answer.get("classified") and "n/a"),
             " option=`%s`" % answer["option"] if answer.get("option") else "",
             " error_kind=`%s`" % answer["error_kind"] if answer.get("error_kind") else ""))
        w("- gate result: **%s**" % replay["gate"]["gate_result"])
        if replay.get("discarded"):
            w("- discarded reason: `%s`" % replay["discard_reason"])
        if replay.get("hypothetical_intent"):
            intent = replay["hypothetical_intent"]
            w("- hypothetical intent: `%s` — draft_proposal=%s external_delivery=%s "
              "schedules_timer=%s injection=%s"
              % (intent["hypothetical_intent"], intent["produces_draft_proposal"],
                 intent["external_delivery"], intent["schedules_timer"],
                 intent["injection_boundary"]))
        w("- non-execution: %s" % replay.get("release_note", ""))
        w("")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixtures", default=DEFAULT_FIXTURES)
    ap.add_argument("--cases", default=DEFAULT_CASES)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true",
                    help="run the contract unit tests and exit 0/1")
    ap.add_argument("--prepare-only", action="store_true",
                    help="only export prepared tasks JSONL (no replay reports)")
    ap.add_argument("--no-run", action="store_true",
                    help="with --check, skip writing reports")
    args = ap.parse_args(argv)

    if args.check:
        import subprocess
        failures = 0
        for name in ("test_decision_schema.py", "test_decision_lab.py"):
            rc = subprocess.call([sys.executable, os.path.join(_HERE, name)],
                                 cwd=os.getcwd())
            if rc != 0:
                failures += 1
        if failures:
            return 1
        if args.no_run:
            return 0

    try:
        data, records, violations = run_suite(args.fixtures, args.cases, prepare_only=args.prepare_only)
        tasks_jsonl = _tasks_jsonl(records)
    except Exception as exc:  # fixture/CLI error
        sys.stderr.write("failed to run decision suite: %s\n" % exc)
        return 2

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "tasks.jsonl"), "w", encoding="utf-8") as fh:
        fh.write(tasks_jsonl)
    sys.stdout.write("wrote tasks.jsonl\n")

    if not args.prepare_only:
        with open(os.path.join(args.out, "replay.json"), "w", encoding="utf-8") as fh:
            fh.write(render_replay_json(data, records, violations))
        with open(os.path.join(args.out, "replay.md"), "w", encoding="utf-8") as fh:
            fh.write(render_replay_markdown(data, records, violations))
        sys.stdout.write("wrote replay.json / replay.md\n")

    if violations:
        for case_id, violation in violations:
            sys.stderr.write("VIOLATION %s: %s\n" % (case_id, violation))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
