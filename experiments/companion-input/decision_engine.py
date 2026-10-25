"""Prepare / replay engine for the typed heartbeat decision experiment.

Pure standard library.  No HTTP, no credentials, no model call.  This reuses
the canonical companion-input engine (:mod:`run_session`) for *source
selection* and *admission* -- it does **not** copy a scheduler.

Contract in one breath
----------------------

1. Candidates for a decision task come only from the existing fixtures, via an
   explicit ``(fixture, policy, placement, history)`` selection.
2. A candidate that the canonical placement/admission already skipped or
   dropped produces **no** decision task.  It is still written to the audit.
3. A prepared task carries allowlisted evidence extracted from the *actually
   started* packet.  ``scripted_outcomes``, ``scripted_produced_results``,
   ``expected`` labels and future sources are stripped.
4. Coalesced candidates keep their constituent provenance but yield a single
   task, not one task per original member.
5. The task is a repository-owned contract (``heartbeat_activity`` with five
   options).  It is explicitly **not** any provider's wire body.
6. Replay reads a *synthetic* answer and classifies it as ``ok`` / ``unknown``
   / ``refusal`` / ``error``.  A refusal, error or unknown is never rewritten
   into a business option.
7. An answer is bound to a task identity and an observed **state revision**.
   Consumption re-checks the snapshot revision plus cancel/end/chat/busy state;
   a late or invalidated answer is only recorded as ``discarded`` and never
   releases activity.
8. Even ``prepare_contact`` yields a draft proposal only.  External delivery is
   always false.

This is shadow annotation: a chosen option is recorded as a *hypothetical
intent*.  It does not recompute future history or internal results.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Tuple

import run_session as rs
import decision_schema as ds


# ---------------------------------------------------------------------------
# Canonical-engine reuse (no second scheduler)
# ---------------------------------------------------------------------------

def load_fixture_raw(fixtures_dir: str, name: str) -> Dict[str, Any]:
    return rs.load_json("%s/%s" % (fixtures_dir.rstrip("/"), name))


def _build_fixture(raw: Dict[str, Any],
                   extra: Iterable[Dict[str, Any]]) -> "rs.Fixture":
    """Build a canonical Fixture, optionally with synthetic override events.

    ``extra`` lets a case express a later world (a correction that arrived, a
    fresh chat window, a busy window) without editing the base fixture.  It is
    synthetic all the way down and never touches real state.
    """
    merged = deepcopy(raw)
    merged["timeline"] = list(merged.get("timeline", [])) + deepcopy(list(extra))
    return rs.Fixture(merged)


def run_selection(fixtures_dir: str, selection: Dict[str, Any],
                  extra: Iterable[Dict[str, Any]] = ()) -> Dict[str, Any]:
    """Run the canonical comparison for one explicit selection."""
    raw = load_fixture_raw(fixtures_dir, selection["fixture"])
    fx = _build_fixture(raw, extra)
    report = rs.run_comparison(fx, selection["policy"], selection["placement"],
                               selection["history"])
    return {"raw": raw, "fixture": fx, "report": report, "selection": selection}


def _find_wake(report: Dict[str, Any], wake_id: str) -> Optional[Dict[str, Any]]:
    for wake in report["wakes"]:
        if wake["id"] == wake_id:
            return wake
        if wake_id in wake.get("coalesced_trigger_ids", []):
            return wake
    return None


# ---------------------------------------------------------------------------
# Allowlisted evidence extraction (drops gold / future / scripted fields)
# ---------------------------------------------------------------------------

#: Fields that must never appear in a prepared task (leaked to the model).
FORBIDDEN_TASK_KEYS = (
    "scripted_outcomes",
    "scripted_produced_results",
    "expected",
    "outcomes",
    "source_archive",
    "excluded_source_ids",
)


def _history_text(entry: Dict[str, Any]) -> str:
    for key in ("body", "exact_user_text", "text"):
        value = entry.get(key)
        if isinstance(value, str):
            return value
    return ""


def _placement_read_only(fixture: "rs.Fixture", selection: Dict[str, Any]) -> List[str]:
    for placement in fixture.placements:
        if placement["id"] == selection["placement"]:
            return list(placement.get("read_only_main_snapshots", []))
    return []


def extract_observed_state(packet: Dict[str, Any], fixture: "rs.Fixture",
                           actual_start: int,
                           selection: Optional[Dict[str, Any]] = None,
                           target: str = "main") -> Dict[str, Any]:
    """Extract allowlisted evidence from an admitted packet.

    Only *current* blocks are carried as current; a defensive filter drops any
    block whose backing source occurrence is strictly in the future of
    ``actual_start``.  Permitted emitted history / explicit carryover is carried
    with its text but flagged ``historical`` and never asserted current.  Future,
    unshared or UI-only material is refused.  Diagnostic ``excluded`` ids are
    NOT evidence and are kept out of this structure.
    """
    def source_time(block_id: str) -> int:
        occ = fixture.by_id.get(block_id)
        return occ["t"] if occ else -1

    def current(block_id: str) -> bool:
        return source_time(block_id) <= actual_start

    observed: Dict[str, Any] = {
        "fresh_ambient": [
            {"id": a["id"], "text": a["text"], "observed_at": a["observed_at"],
             "expires_at": a["expires_at"]}
            for a in packet.get("fresh_ambient_blocks", []) if current(a["id"])
        ],
        "memory": [
            {"id": m["id"], "text": m["text"]}
            for m in packet.get("memory_items", []) if current(m["id"])
        ],
        "human_messages": [
            {
                "id": h["id"], "exact_user_text": h["exact_user_text"],
                "origin": h["origin"], "access": h["access"],
                "wrapper": h["wrapper"],
            }
            for h in packet.get("user_text_blocks", []) if current(h["id"])
        ],
        "passive_recall": [
            {"id": r["id"], "supplied_by": r["supplied_by"], "body": r["body"],
             "source_memory_id": r["source_memory_id"]}
            for r in packet.get("passive_recall_blocks", []) if current(r["id"])
        ],
        # Prior internal results were produced BEFORE this wake.  They are
        # retained with a historical identity -- they are not current facts and
        # never include the result this (not-yet-executed) turn would produce.
        "prior_internal_results": [
            {"id": b["id"], "body": b["body"], "status": b["status"],
             "delivered": False, "historical": True}
            for b in packet.get("internal_result_blocks", []) if current(b["id"])
        ],
        "historical_material_note": (
            "Historical material is labelled historical=True; it is NOT "
            "asserted current and must not be read as fresh state."
        ),
        "historical_material": [],
    }

    # Permitted emitted history / explicit carryover, with text preserved and an
    # explicit historical marker.  Refuse future / unshared / UI-only material.
    read_only = set(_placement_read_only(fixture, selection)) if selection else set()
    for entry in packet.get("carried_history_or_carryover", []):
        eid = entry.get("id")
        if not eid:
            continue
        occ = fixture.by_id.get(eid)
        if occ is not None:
            if occ["t"] > actual_start:
                continue  # future material is not permitted history
            if occ.get("ui_only"):
                continue  # UI-only never enters model evidence
            if occ["type"] == "human_message" and target == "independent" and eid not in read_only:
                continue  # unshared main snapshot
        observed["historical_material"].append({
            "id": eid,
            "kind": entry.get("kind", "history"),
            "historical": True,
            "text": _history_text(entry),
        })

    return observed


def _external_evidence(fixture: "rs.Fixture", selection: Dict[str, Any],
                       t: int, target: str) -> List[List[Any]]:
    """Canonical source selection at ``t`` for the *external* current sources.

    Uses the same selector the engine uses; internal-result production is
    deliberately excluded so this never peeks at a not-yet-executed turn.
    """
    read_only = _placement_read_only(fixture, selection)
    sel = rs.select_sources(fixture, t, [], target, read_only)
    evidence: List[List[Any]] = []
    for a in sel["fresh_ambient_blocks"]:
        evidence.append(["ambient", a["id"], a.get("text", ""), a.get("expires_at")])
    for m in sel["memory_items"]:
        evidence.append(["memory", m["id"], m.get("text", "")])
    for h in sel["human_blocks"]:
        evidence.append(["human", h["id"], h["exact_user_text"]])
    for r in sel["recall_blocks"]:
        evidence.append(["recall", r["id"], r["body"]])
    return evidence


def dependency_signature(fixture: "rs.Fixture", selection: Dict[str, Any],
                         t: int, target: str) -> str:
    """Hash of the external current sources at ``t`` (the decision's deps)."""
    canonical = json.dumps(
        sorted(_external_evidence(fixture, selection, t, target),
               key=lambda row: (row[0], row[1])),
        sort_keys=True, ensure_ascii=False,
    )
    return "dep-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def state_revision(observed: Dict[str, Any], execution_target: str,
                   actual_start: int) -> str:
    """Deterministic hash of the *external current* state a decision binds to.

    ``prior_internal_results`` are deliberately excluded: an internal result
    produced *after* this wake's start is not an input of this turn and must not
    invalidate it.  Those results are still carried in the task as history.
    """
    observed_for_hash = {
        k: v for k, v in observed.items() if k != "prior_internal_results"
    }
    canonical = json.dumps(
        {"observed": observed_for_hash, "execution_target": execution_target,
         "actual_start": actual_start},
        sort_keys=True, ensure_ascii=False,
    )
    return "rev-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Task preparation
# ---------------------------------------------------------------------------

def _task_id(selection: Dict[str, Any], wake_id: str) -> str:
    return "%s::%s::%s::%s::%s" % (
        selection["fixture"].rsplit(".", 1)[0], selection["policy"],
        selection["placement"], selection["history"], wake_id)


def build_task(selection: Dict[str, Any], fixture: "rs.Fixture",
               wake: Dict[str, Any], packet: Dict[str, Any]) -> Dict[str, Any]:
    """One decision task for one ADMITTED wake (a coalesced burst is one task)."""
    start = wake["actual_start"]
    target = wake["execution_target"]
    observed = extract_observed_state(packet, fixture, start, selection, target)
    task = {
        "task_id": _task_id(selection, wake["id"]),
        "task_kind": ds.TASK_KIND,
        "not_a_provider_wire_body": True,
        "contract_note": (
            "Repository-owned bounded-choice contract. NOT any provider's tool "
            "schema, JSON mode or function-call payload."
        ),
        "question": {
            "prompt": "What should this autonomous opportunity do?",
            "options": [
                {"option": opt, "label": ds.OPTION_INFO[opt]["label"],
                 "note": ds.OPTION_INFO[opt]["note"]}
                for opt in ds.OPTIONS
            ],
        },
        "selection": dict(selection),
        "candidate": {
            "wake_id": wake["id"],
            "coalesced": wake["coalesced"],
            "coalesced_trigger_ids": list(wake.get("coalesced_trigger_ids", [])),
            "constituents": [
                {"id": c["id"], "owner_kind": c["owner_kind"],
                 "owner_detail": c["owner_detail"], "trigger_time": rs.format_time(c["trigger_time"]),
                 "reasons": list(c["reasons"])}
                for c in wake["candidates"]
            ],
        },
        "trigger_owner": {
            "kind": wake["owner_kind"], "detail": wake["owner_detail"],
        },
        "execution_target": wake["execution_target"],
        "actual_start": rs.format_time(start),
        "actual_start_s": start,
        "placement_context": {
            "rule": wake.get("placement_rule"),
            "turn_busy_at_trigger": wake.get("turn_busy_at_trigger"),
            "chat_active_at_trigger": wake.get("chat_active_at_trigger"),
            "deferred": wake["deferred"],
            "placement_reason": wake.get("placement_reason"),
        },
        "state_revision": None,  # filled after observed state is known
        "dependency_signature": dependency_signature(fixture, selection, start, target),
        "observed_state": observed,
        "recheck_note": (
            "Consumption re-verifies this revision plus cancel/end/chat/busy "
            "state in a synthetic snapshot; it does not claim to detect real "
            "Claude Code state."
        ),
    }
    task["state_revision"] = state_revision(observed, target, start)
    _assert_clean_task(task)
    return task


def _assert_clean_task(task: Dict[str, Any]) -> None:
    for forbidden in FORBIDDEN_TASK_KEYS:
        if forbidden in task or forbidden in task.get("observed_state", {}):
            raise AssertionError("prepared task leaked %r" % forbidden)


def prepare(fixtures_dir: str, selection: Dict[str, Any],
            extra: Iterable[Dict[str, Any]] = ()) -> Dict[str, Any]:
    """Prepare decision tasks for one selection, honouring canonical admission.

    Returns ``{"tasks": [...], "audit": {...}}``.  Skipped/dropped candidates
    never become tasks; they appear under ``audit`` instead.
    """
    result = run_selection(fixtures_dir, selection, extra)
    fixture, report = result["fixture"], result["report"]
    packets = {p["wake"]["candidate_id"]: p for p in report["packets"]}
    tasks = [
        build_task(selection, fixture, wake, packets[wake["id"]])
        for wake in report["wakes"]
    ]
    audit = {
        "selection": dict(selection),
        "admitted_wake_ids": [w["id"] for w in report["wakes"]],
        "task_ids": [t["task_id"] for t in tasks],
        "skipped_ids": report["audit"]["skipped_ids"],
        "skipped_reasons": report["audit"]["skipped_reasons"],
        "dropped_ids": report["audit"]["dropped_ids"],
        "dropped_reasons": report["audit"]["dropped_reasons"],
        "blocked_candidates": (
            [{"id": i, "reason": report["audit"]["skipped_reasons"].get(i),
              "fate": "skipped"} for i in report["audit"]["skipped_ids"]]
            + [{"id": i, "reason": report["audit"]["dropped_reasons"].get(i),
                "fate": "dropped"} for i in report["audit"]["dropped_ids"]]
        ),
        "note": "Blocked candidates are audited only; they produce no task.",
    }
    return {"tasks": tasks, "audit": audit}


def prepare_many(fixtures_dir: str, selections: List[Dict[str, Any]]) -> Dict[str, Any]:
    all_tasks, audits = [], []
    for selection in selections:
        out = prepare(fixtures_dir, selection)
        all_tasks.extend(out["tasks"])
        audits.append(out["audit"])
    return {"tasks": all_tasks, "audits": audits}


# ---------------------------------------------------------------------------
# Consumption (replay) with a real post-check gate
# ---------------------------------------------------------------------------

DISCARD_RUN_ENDED = "run_ended_before_consume"
DISCARD_ANSWER_EARLY = "answer_before_actual_start"
DISCARD_WAKE_GONE = "wake_not_reproduced_or_now_blocked"
DISCARD_RESCHEDULED = "wake_rescheduled_after_observation"
DISCARD_CONSTITUENT_CANCELLED = "constituent_cancelled_before_consume"
DISCARD_REVISION = "state_revision_changed"
DISCARD_CHAT_ACTIVE = "chat_active_at_consume"
DISCARD_TARGET_BUSY = "execution_target_busy_at_consume"
DISCARD_UNKNOWN_TASK = "unknown_task_id"
DISCARD_REVISION_MISMATCH = "bound_revision_mismatch_on_consume"
DISCARD_UNBOUND = "answer_missing_task_binding"


def _gate_state(fixture: "rs.Fixture", consume_time: int,
                execution_target: str) -> Dict[str, Any]:
    run_end = fixture.run_end_t
    return {
        "consume_time_s": consume_time,
        "run_end_t": run_end,
        "after_run_end": run_end is not None and consume_time >= run_end,
        "chat_active": fixture.in_chat(consume_time),
        "target_busy": fixture.in_busy(consume_time, execution_target),
    }


def _cancel_time(fixture: "rs.Fixture", plan_id: str) -> Optional[int]:
    for occ in fixture.occurrences:
        if occ.get("type") == "cancel" and occ.get("target") == plan_id:
            return occ["t"]
    return None


def binding_rejection(task: Dict[str, Any], answer: Any) -> Optional[str]:
    """Enforce that an answer is bound to this task's id + revision.

    Returns a discard reason when the binding is missing or wrong, else None.
    The binding is the *consume entry* contract, not a promise the provider
    echoes it back; the runner attaches it explicitly.
    """
    if not isinstance(answer, dict):
        return DISCARD_UNBOUND
    if "task_id" not in answer or "state_revision" not in answer:
        return DISCARD_UNBOUND
    if answer["task_id"] != task["task_id"]:
        return DISCARD_UNKNOWN_TASK
    if answer["state_revision"] != task["state_revision"]:
        return DISCARD_REVISION_MISMATCH
    return None


def consume(fixtures_dir: str, task: Dict[str, Any], answer: Any,
            consume_time_s: int, consume_overrides: Iterable[Dict[str, Any]] = (),
            ) -> Dict[str, Any]:
    """Consume a synthetic answer against a prepared task, with a real gate.

    The post-check is a *synthetic snapshot supplied state*: it re-runs the
    canonical engine with the case's ``consume_overrides`` and verifies
    binding / cancel / end / dependency / chat / busy.  It makes no claim to
    observe real Claude Code.

    Order of checks (each failing one only discards, never releases):

    1. the answer must be explicitly bound to this task id + state revision;
    2. a pre-start answer is rejected;
    3. the wake must still be reproduced at the same start (a cancel before
       start changes admission, so this also catches that);
    4. no participating self-wake reason may have been cancelled between the
       observed start and the consume time;
    5. the external dependencies selected at the *consume* time must equal those
       at the observed start (weather expiry / memory correction in between);
    6. run-end, active chat and target-busy at the consume time.
    """
    binding = binding_rejection(task, answer)
    if binding is not None:
        return _discard_result(task, answer, consume_time_s, binding, None)

    if consume_time_s < task["actual_start_s"]:
        return _discard_result(task, answer, consume_time_s, DISCARD_ANSWER_EARLY, None)

    result = run_selection(fixtures_dir, task["selection"], consume_overrides)
    fixture, report = result["fixture"], result["report"]
    gate = _gate_state(fixture, consume_time_s, task["execution_target"])

    wake = _find_wake(report, task["candidate"]["wake_id"])
    if wake is None:
        return _discard_result(task, answer, consume_time_s, DISCARD_WAKE_GONE, gate)
    if wake["actual_start"] != task["actual_start_s"]:
        return _discard_result(task, answer, consume_time_s, DISCARD_RESCHEDULED, gate)
    if gate["after_run_end"]:
        return _discard_result(task, answer, consume_time_s, DISCARD_RUN_ENDED, gate)

    # Late cancellation of any participating self-wake reason (including a
    # constituent of a coalesced burst) invalidates the whole old task.
    # Inspect the reasons that the answer actually saw, including a member
    # removed by today's canonical admission while the rest of its burst survives.
    for constituent in task["candidate"]["constituents"]:
        if constituent["owner_kind"] != "self_wake":
            continue
        cancelled = _cancel_time(fixture, constituent["id"])
        if cancelled is not None and cancelled <= consume_time_s:
            return _discard_result(task, answer, consume_time_s,
                                   DISCARD_CONSTITUENT_CANCELLED, gate, {
                                       "cancelled_constituent": constituent["id"],
                                       "cancelled_at_s": cancelled})

    # External dependencies may have changed BETWEEN the observed start and the
    # consume time (fresh -> corrected -> expired).  Re-select at consume time.
    deps_now = dependency_signature(
        fixture, task["selection"], consume_time_s, task["execution_target"])
    if deps_now != task["dependency_signature"]:
        return _discard_result(task, answer, consume_time_s, DISCARD_REVISION, gate, {
            "dependency_at_start": task["dependency_signature"],
            "dependency_at_consume": deps_now,
        })

    if task["execution_target"] == "main" and gate["chat_active"]:
        return _discard_result(task, answer, consume_time_s, DISCARD_CHAT_ACTIVE, gate)
    if gate["target_busy"]:
        return _discard_result(task, answer, consume_time_s, DISCARD_TARGET_BUSY, gate)

    payload = {k: v for k, v in answer.items()
               if k not in ("task_id", "state_revision")}
    classified = ds.classify_answer(payload)
    if classified["status"] != ds.STATUS_OK:
        return {
            "task_id": task["task_id"],
            "state_revision": task["state_revision"],
            "consume_time": rs.format_time(consume_time_s),
            "gate": dict(gate, gate_result="not_released_non_ok_answer"),
            "discarded": False,
            "discard_reason": None,
            "release_note": "non-ok answer is never rewritten into a business option",
            "answer": classified,
            "hypothetical_intent": None,
            "released": False,
            "external_delivery": False,
        }

    intent = ds.hypothetical_intent(classified["option"], task["execution_target"])
    return {
        "task_id": task["task_id"],
        "state_revision": task["state_revision"],
        "consume_time": rs.format_time(consume_time_s),
        "gate": dict(gate, gate_result="released"),
        "discarded": False,
        "discard_reason": None,
        "answer": classified,
        "hypothetical_intent": intent,
        "released": bool(intent["releases_activity"]),
        "release_note": (
            "Shadow annotation only: no activity, injection, message or timer "
            "is actually performed."
        ),
        "external_delivery": False,
    }


def _discard_result(task: Dict[str, Any], answer: Any, consume_time_s: int,
                    reason: str, gate: Optional[Dict[str, Any]],
                    extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result = {
        "task_id": task["task_id"],
        "state_revision": task["state_revision"],
        "consume_time": rs.format_time(consume_time_s),
        "gate": dict(gate, gate_result="discarded") if gate else {
            "gate_result": "discarded"},
        "discarded": True,
        "discard_reason": reason,
        "release_note": "late or invalidated answer is recorded only; no activity released",
        "answer": {"classified": False, "raw": answer},
        "hypothetical_intent": None,
        "released": False,
        "external_delivery": False,
    }
    if extra:
        result["discard_detail"] = extra
    return result
