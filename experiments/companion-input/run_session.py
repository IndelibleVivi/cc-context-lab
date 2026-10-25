"""Synthetic wake engine for the companion-input comparison lab.

Two independent axes are compared here:

1. **Trigger axis** — which *trigger policy* proposes autonomous opportunities
   (fixed interval, listed-jitter interval, event driven, self-scheduled
   one-shots, idle window, hybrid).  This axis only answers "when did an
   opportunity arise".
2. **Placement axis** — where an admitted autonomous opportunity is allowed to
   *execute* relative to the main human conversation (main_skip, main_defer,
   independent).  This axis owns skipping/deferral/coalescing and the choice of
   execution target (main thread vs an independent autonomous session).

Key distinctions this lab keeps explicit:

* **Trigger owner/location != execution target.**  A trigger can originate from
  an external timer/event and still target the main conversation; an external
  origin does not by itself imply independent execution.
* **turn_busy != chat_active.**  ``turn_busy`` is one response still running;
  ``chat_active`` is an explicitly supplied fact that a human conversation is
  ongoing across turns.  The lab never infers chat inactivity from the model
  finishing one response.
* **same_session != main_session.**  An independent execution target's
  "same session" history is that session's OWN accumulated history; the main
  conversation's snapshots are only ever explicit, read-only fixture inputs.

Everything is fixture-driven: no real clock, sleep, thread, network, model or
message delivery.  Output is a HYPOTHETICAL packet built by this lab, NOT a
captured Claude Code request.
"""

import json
from copy import deepcopy
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_time(seconds: int) -> str:
    return "%02d:%02d:%02d" % (seconds // 3600, (seconds % 3600) // 60, seconds % 60)

def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

class Fixture(object):
    """A synthetic scenario: a timeline plus trigger-policy and placement specs.

    Occurrence types:

      tick            observation point for the idle-window policy
      busy_interval   turn_busy window: a response/turn is running
      chat_interval   chat_active window: a human conversation is ongoing across
                      turns (explicitly supplied; never inferred)
      human_message   incoming human channel message: verbatim body + metadata
      ambient         present/ambient fact (weather/location) with observation
                      and expiry times
      ambient_expire  removal of a snapshot (it stays in the archive)
      memory          durable note; may ``corrects`` an earlier id
      passive_recall  already-supplied recall text (fixture input, no backend)
      internal        scripted internal-only outcome
      self_wake       explicit one-shot plan (fixture decision)
      cancel          scripted stop/cancel of a pending plan
      run_end         silent end of the run
    """

    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.scenario_id = raw["scenario_id"]
        self.description = raw.get("description", "")
        self.policies = raw["policies"]
        self.placements = raw["placements"]
        self.shared = raw["shared"]
        self.outcomes = raw["outcomes"]
        self.scenario_assumptions = raw.get("assumptions", "")

        self.occurrences: List[Dict[str, Any]] = list(raw["timeline"])

        self.by_id: Dict[str, Dict[str, Any]] = {}
        self.self_wakes: Dict[str, Dict[str, Any]] = {}
        for occ in self.occurrences:
            if occ.get("id"):
                self.by_id[occ["id"]] = occ
            if occ.get("type") == "self_wake":
                self.self_wakes[occ["id"]] = occ

        # Run-end / stop time: no wake may start at or after this.
        self.run_end_t = None
        for occ in self.occurrences:
            if occ.get("type") == "run_end":
                self.run_end_t = occ["t"]

    # -- accessors ----------------------------------------------------------

    def events(self) -> List[Dict[str, Any]]:
        return sorted(
            [o for o in self.occurrences if o["type"] != "tick"],
            key=lambda o: (o["t"], o["id"]),
        )

    def ticks(self) -> List[Dict[str, Any]]:
        return sorted(
            [o for o in self.occurrences if o["type"] == "tick"],
            key=lambda o: (o["t"], o["id"]),
        )

    def periodic_ticks(self, policy):
        # A fixed cadence comes from the interval, never an irregular event list.
        horizon = self.raw["duration_seconds"]
        return [{"id": "periodic-%d" % i, "t": t}
                for i, t in enumerate(range(0, horizon + 1,
                                            policy.get("interval_seconds", 300)))]

    def busy_windows(self) -> List[Dict[str, Any]]:
        return [o for o in self.occurrences if o.get("type") == "busy_interval"]

    def chat_windows(self) -> List[Dict[str, Any]]:
        return [o for o in self.occurrences if o.get("type") == "chat_interval"]

    def internal_by_id(self, iid: str) -> Optional[Dict[str, Any]]:
        for o in self.occurrences:
            if o.get("type") == "internal" and o.get("id") == iid:
                return o
        return None

    def cancel_time(self, plan_id: str) -> Optional[int]:
        for o in self.occurrences:
            if o.get("type") == "cancel" and o.get("target") == plan_id:
                return o["t"]
        return None

    def in_busy(self, t: int, session: str = "main") -> bool:
        """turn_busy for a given execution session.  A busy_interval may name its
        ``session`` (default ``main``), so an independent session has its own."""
        for o in self.busy_windows():
            if o.get("session", "main") == session and o["t"] <= t < o["end"]:
                return True
        return False

    def in_chat(self, t: int) -> bool:
        """chat_active as a half-open window [t, end).

        A wake that starts at exactly ``end`` begins after the conversation, so
        it is *not* during chat_active.  (The coalesced main_defer burst is
        emitted at ``end`` by design.)  The turn-gap where turn_busy=false but
        chat_active=true is interior to this window."""
        for o in self.chat_windows():
            if o["t"] <= t < o["end"]:
                return True
        return False

# ---------------------------------------------------------------------------
# Trigger axis: candidate opportunities
# ---------------------------------------------------------------------------

def _cand(cid, owner_kind, owner_detail, t, reasons, carryover=None):
    """A candidate autonomous opportunity, before placement decides fate."""
    return {
        "id": cid,
        "owner_kind": owner_kind,          # timer | event | self_wake | idle
        "owner_detail": owner_detail,      # e.g. "external_timer", "in_session"
        "trigger_time": t,
        "reasons": list(reasons),
        "carryover": carryover or [],
    }

def generate_candidates(fx: Fixture, policy: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Trigger axis only: produce the raw opportunities a policy proposes.

    Nothing here skips, defers, coalesces, or chooses a target — that is the
    placement axis' job.  Each candidate records where its trigger *originates*
    (``owner_kind``/``owner_detail``); this is deliberately separate from the
    execution target chosen later.
    """
    kind = policy["kind"]
    cands: List[Dict[str, Any]] = []

    if kind == "fixed_interval":
        interval = policy.get("interval_seconds", 300)
        for i, tick in enumerate(fx.periodic_ticks(policy)):
            cands.append(_cand(
                "fixed-%d" % i, "timer", "external_timer", tick["t"],
                ["fixed_interval:%ds" % interval, "tick_id:%s" % tick["id"]],
            ))

    elif kind == "jittered_interval":
        offsets = policy["jitter_offsets_seconds"]
        for i, tick in enumerate(fx.periodic_ticks(policy)):
            off = offsets[i % len(offsets)]
            cands.append(_cand(
                "jitter-%d" % i, "timer", "external_timer", tick["t"] + off,
                ["jittered_interval:base=%ds" % policy.get("interval_seconds", 300),
                 "listed_offset:%+ds" % off],
            ))

    elif kind == "event_driven":
        events = policy.get("events", ["human_message", "ambient", "memory"])
        for ev in fx.events():
            if ev["type"] not in events or ev.get("ui_only"):
                continue
            cands.append(_cand(
                "event-%s" % ev["id"], "event", "external_event", ev["t"],
                ["event:%s" % ev["type"], "event_id:%s" % ev["id"]],
            ))

    elif kind == "self_wake":
        for plan in sorted(fx.occurrences, key=lambda o: (o["t"], o["id"])):
            if plan.get("planned_for") is None or plan.get("disabled"):
                continue
            cands.append(_cand(
                plan["id"], "self_wake", "in_session_plan", int(plan["planned_for"]),
                ["self_wake_plan:%s" % plan["id"]],
                carryover=plan.get("carryover", []),
            ))

    elif kind == "idle_window":
        idle_after = policy.get("idle_after_seconds", 600)
        for tick in fx.ticks():
            t = tick["t"]
            ws = t - idle_after
            recent = [ev for ev in fx.events()
                      if ev["type"] == "human_message" and ws <= ev["t"] <= t]
            if t >= idle_after and not recent:
                cands.append(_cand(
                    "idle-%s" % tick["id"], "idle", "in_session_idle", t,
                    ["idle_window:%ds_observed_no_human_activity" % idle_after,
                     "idle_definition:observed_runtime_activity_only",
                     "not_an_inference_of_sleep_or_mood"],
                ))
                break  # one idle opportunity; a later burst is not a storm

    elif kind == "hybrid":
        for tick in fx.periodic_ticks(policy):
            cands.append(_cand(
                "hybrid-tick-%s" % tick["id"], "timer", "external_timer", tick["t"],
                ["timer:periodic_tick", "tick_id:%s" % tick["id"]],
            ))
        for ev in fx.events():
            if ev["type"] in ("human_message", "ambient", "memory") and not ev.get("ui_only"):
                cands.append(_cand(
                    "hybrid-evt-%s" % ev["id"], "event", "external_event", ev["t"],
                    ["event:%s" % ev["type"], "event_id:%s" % ev["id"]],
                ))
        for plan in fx.occurrences:
            if plan.get("planned_for") is None or plan.get("disabled"):
                continue
            cands.append(_cand(
                plan["id"], "self_wake", "in_session_plan", int(plan["planned_for"]),
                ["self_wake_plan:%s" % plan["id"]],
                carryover=plan.get("carryover", []),
            ))

    return sorted(cands, key=lambda c: (c["trigger_time"], c["id"]))

# ---------------------------------------------------------------------------
# Placement axis: admit/skip/defer/coalesce and choose execution target
# ---------------------------------------------------------------------------

def place_candidates(fx: Fixture, placement: Dict[str, Any],
                     candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Resolve actual starts against the target's turn and main chat windows.

    This is an offline placement rule. No model turn duration is inferred: all
    occupancy intervals are fixture inputs. Equal resolved starts coalesce.
    Individual candidates survive grouping so admission can still cancel one.
    """
    target, rule = placement["target"], placement["rule"]
    groups, skipped = {}, []
    for candidate in candidates:
        c = dict(candidate,
                 turn_busy_at_trigger=fx.in_busy(candidate["trigger_time"], target),
                 chat_active_at_trigger=fx.in_chat(candidate["trigger_time"]))
        t = c["trigger_time"]
        while True:
            chat_ends = [o["end"] for o in fx.chat_windows()
                         if target == "main" and o["t"] <= t < o["end"]]
            if chat_ends and rule == "main_skip":
                skipped.append(dict(c, placement_reason="skipped_during_chat_active"))
                break
            busy_ends = [o["end"] for o in fx.busy_windows()
                         if o.get("session", "main") == target and o["t"] <= t < o["end"]]
            ends = chat_ends + busy_ends
            if ends:
                t = max(ends)
                continue  # a turn end may land in another active chat/turn
            groups.setdefault(t, []).append(c)
            break
    return {"groups": groups, "skipped": skipped, "placement": placement}


def _merge_wake(members, t, placement):
    merged = len(members) > 1
    reasons = [r for c in members for r in c["reasons"]]
    if merged:
        reasons += ["coalesced_trigger_id:" + c["id"] for c in members]
    deferred = any(c["trigger_time"] < t for c in members)
    def sole(field):
        values = {c[field] for c in members}
        return next(iter(values)) if len(values) == 1 else "mixed"
    return {
        "id": "burst-%d" % t if merged else members[0]["id"],
        "owner_kind": sole("owner_kind"), "owner_detail": sole("owner_detail"),
        "execution_target": placement["target"], "placement_rule": placement["rule"],
        "trigger_time": min(c["trigger_time"] for c in members), "actual_start": t,
        "reasons": sorted(set(reasons)),
        "carryover": sorted({x for c in members for x in c["carryover"]}),
        "deferred": deferred, "coalesced": merged,
        "coalesced_trigger_ids": [c["id"] for c in members] if merged else [],
        "candidates": members,
        "turn_busy_at_trigger": any(c["turn_busy_at_trigger"] for c in members),
        "chat_active_at_trigger": any(c["chat_active_at_trigger"] for c in members),
        "placement_reason": "coalesced_at_allowed_start" if merged else (
            "deferred_to_allowed_start" if deferred else "admitted_at_trigger"),
    }


def admit(fx: Fixture, placed: Dict[str, Any]) -> Dict[str, Any]:
    admitted, dropped, consumed = [], [], []
    for t, candidates in sorted(placed["groups"].items()):
        eligible = []
        for c in candidates:
            reason = None
            if fx.run_end_t is not None and t >= fx.run_end_t:
                reason = "after_run_end"
            elif c["owner_kind"] == "self_wake":
                cancelled = fx.cancel_time(c["id"])
                if cancelled is not None and cancelled <= t:
                    reason = "cancelled_before_actual_start"
            if reason:
                dropped.append(dict(c, actual_start=t, drop_reason=reason))
            else:
                eligible.append(c)
                if c["owner_kind"] == "self_wake":
                    consumed.append(c["id"])
        if eligible:
            admitted.append(_merge_wake(eligible, t, placed["placement"]))
    return {"admitted": admitted, "dropped": dropped,
            "skipped": placed["skipped"], "consumed_self_wake_ids": consumed}

def run_placement(fx: Fixture, policy: Dict[str, Any],
                  placement: Dict[str, Any]) -> Dict[str, Any]:
    """Full pipeline for one (trigger policy, placement): generate -> place ->
    admit.  Returns admitted wakes plus the skip/drop audit."""
    cands = generate_candidates(fx, policy)
    placed = place_candidates(fx, placement, cands)
    final = admit(fx, placed)
    return {
        "policy_id": policy["id"],
        "policy_kind": policy["kind"],
        "placement_id": placement["id"],
        "placement_rule": placement["rule"],
        "placement_target": placement["target"],
        "wakes": final["admitted"],
        "audit": {
            "skipped_ids": [s["id"] for s in final["skipped"]],
            "skipped_reasons": {s["id"]: s["placement_reason"] for s in final["skipped"]},
            "dropped_ids": [d["id"] for d in final["dropped"]],
            "dropped_reasons": {d["id"]: d["drop_reason"] for d in final["dropped"]},
            "coalesced_trigger_ids": [c for w in final["admitted"] for c in w["coalesced_trigger_ids"]],
            "consumed_self_wake_ids": final["consumed_self_wake_ids"],
        },
    }

# ---------------------------------------------------------------------------
# Packet assembly: current input at ACTUAL start
# ---------------------------------------------------------------------------

class SessionLedger:
    """Only material actually delivered to, or produced by, this session."""
    def __init__(self, session_identity, read_only_sources=None):
        self.session_identity = session_identity
        self.read_only_sources = read_only_sources or []
        self.entries = {}

    def note_emitted(self, packet):
        for field in ("user_text_blocks", "fresh_ambient_blocks", "memory_items",
                      "passive_recall_blocks"):
            for block in packet[field]:
                self.entries[block["id"]] = dict(deepcopy(block), kind="history:" + field)

    def note_produced(self, blocks):
        for block in blocks:
            self.entries[block["id"]] = dict(deepcopy(block), kind="history:internal_result")

# ---------------------------------------------------------------------------
# Source selection (fixture state) at a given actual start
# ---------------------------------------------------------------------------

def build_source_state(fx: Fixture, t: int) -> Dict[str, Any]:
    """Apply all fixture occurrences with time <= t and return the source view.

    This is the fixture's ground truth at ``t`` (what *exists*), independent of
    what any session has actually emitted.
    """
    live_ambient = []
    archived_ambient = []
    human_ids = []
    memories = []
    corrections = {}

    for occ in fx.events():
        if occ["t"] > t:
            continue
        typ = occ["type"]
        if typ == "human_message":
            human_ids.append(occ["id"])
        elif typ == "ambient":
            live_ambient.append(occ["id"])
        elif typ == "ambient_expire":
            if occ["target"] in live_ambient:
                live_ambient.remove(occ["target"])
            if occ["target"] not in archived_ambient:
                archived_ambient.append(occ["target"])
        elif typ == "memory":
            memories.append(occ["id"])
            if occ.get("corrects"):
                corrections[occ["corrects"]] = occ["id"]

    return {
        "live_ambient": live_ambient,
        "archived_ambient": archived_ambient,
        "human_ids": human_ids,
        "memories": memories,
        "corrections": corrections,
    }

def select_sources(fx: Fixture, t: int, produced_internals: List[str],
                   target="main", read_only_sources=()) -> Dict[str, Any]:
    """Reselect every source revision at actual start ``t`` with reasons."""
    state = build_source_state(fx, t)
    included: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []

    # --- fresh ambient -------------------------------------------------
    fresh_ambient = []
    for aid in state["live_ambient"]:
        occ = fx.by_id[aid]
        if occ.get("ui_only"):
            excluded.append({"id": aid, "kind": "ambient", "reason": "ui_only:not_submitted"})
            continue
        obs = occ.get("observed_at", occ["t"])
        exp = occ.get("expires_at")
        if obs > t:
            excluded.append({"id": aid, "kind": "ambient",
                             "reason": "observed_after_start"})
            continue
        if exp is not None and t >= exp:
            excluded.append({"id": aid, "kind": "ambient",
                             "reason": "expired_at_start (kept in archive, not current)"})
            continue
        fresh_ambient.append(occ)
        included.append({"id": aid, "kind": "ambient",
                         "reason": "fresh: observed<=start<expiry"})
    reported = {e["id"] for e in excluded}
    for aid in state["archived_ambient"]:
        if aid in reported:
            continue
        excluded.append({"id": aid, "kind": "ambient",
                         "reason": "archived_expired (retained, not current)"})

    # --- memory --------------------------------------------------------
    memory_items = []
    for mid in state["memories"]:
        occ = fx.by_id[mid]
        if occ.get("ui_only"):
            excluded.append({"id": mid, "kind": "memory", "reason": "ui_only:not_submitted"})
            continue
        cb = state["corrections"].get(mid)
        if cb:
            excluded.append({"id": mid, "kind": "memory",
                             "reason": "corrected_by:%s (original retained, not current)" % cb})
            continue
        if occ.get("expires_at") is not None and t >= occ["expires_at"]:
            excluded.append({"id": mid, "kind": "memory", "reason": "expired_at_start"})
            continue
        memory_items.append(occ)
        included.append({"id": mid, "kind": "memory", "reason": "memory_active"})

    # --- human message text (verbatim) + wrapper ----------------------
    human_blocks = []
    for mid in state["human_ids"]:
        occ = fx.by_id[mid]
        if occ.get("ui_only"):
            excluded.append({"id": mid, "kind": "human_message", "reason": "ui_only:not_submitted"})
            continue
        if target == "independent" and mid not in read_only_sources:
            excluded.append({"id": mid, "kind": "human_message",
                             "reason": "main_snapshot_not_selected"})
            continue
        included.append({"id": mid, "kind": "human_message", "reason": (
            "read_only_main_snapshot" if target == "independent" else "observed_human_source")})
        human_blocks.append({
            "id": mid,
            "exact_user_text": occ["body"],
            "wrapper_metadata": {
                "channel": occ["channel"], "sender": occ["sender"],
                "sender_time": format_time(occ["sender_time"]),
                "received_at": format_time(occ["t"]),
                "reply_target": occ.get("reply_target"),
                "attachment": occ.get("attachment"),
            },
            "origin": "human_channel_message",
            "access": "read_only_main_snapshot" if target == "independent" else "main_source",
        })

    # --- passive recall (filtered by referenced memory state) ----------
    recall_blocks = []
    for occ in fx.occurrences:
        if occ.get("type") != "passive_recall" or occ["t"] > t:
            continue
        src = occ.get("source_memory_id")
        if occ.get("ui_only"):
            excluded.append({"id": occ["id"], "kind": "passive_recall",
                             "reason": "ui_only:not_submitted"})
            continue
        if src in state["corrections"]:
            excluded.append({"id": occ["id"], "kind": "passive_recall",
                             "reason": "referenced_memory:%s corrected_by:%s"
                                       % (src, state["corrections"][src])})
            continue
        if src is not None:
            sm = fx.by_id.get(src)
            if sm is not None and sm.get("expires_at") is not None and t >= sm["expires_at"]:
                excluded.append({"id": occ["id"], "kind": "passive_recall",
                                 "reason": "referenced_memory:%s expired" % src})
                continue
        if src is not None and src not in {m["id"] for m in memory_items}:
            excluded.append({"id": occ["id"], "kind": "passive_recall",
                             "reason": "source_memory_not_current"})
            continue
        included.append({"id": occ["id"], "kind": "passive_recall", "reason": "supplied_current_recall"})
        recall_blocks.append({
            "id": occ["id"], "supplied_by": occ.get("supplied_by", "fixture"),
            "body": occ["body"], "source_memory_id": src,
        })

    # --- internal-only results (produced before this start) ------------
    internal_blocks = []
    for iid in produced_internals:
        occ = fx.internal_by_id(iid)
        included.append({"id": iid, "kind": "internal", "reason": "prior_result_selected"})
        internal_blocks.append({
            "id": iid,
            "body": occ.get("body", "") if occ else "",
            "status": "internal_only",
            "delivered": False,
        })

    seen = set()
    deduped = []
    for e in excluded:
        key = (e["id"], e["kind"], e["reason"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(e)

    return {
        "included": included, "excluded": deduped,
        "fresh_ambient_blocks": fresh_ambient, "memory_items": memory_items,
        "human_blocks": human_blocks, "recall_blocks": recall_blocks,
        "internal_blocks": internal_blocks,
    }

# ---------------------------------------------------------------------------
# Packet
# ---------------------------------------------------------------------------

def _outcomes_for(fx, wake, policy_id):
    ids = {c["id"] for c in wake["candidates"]}
    exact = [o for o in fx.outcomes if o["trigger"] in ids]
    return exact or [o for o in fx.outcomes if o["trigger"] == policy_id]


def build_packet(fx: Fixture, wake: Dict[str, Any], session_mode: str,
                 ledger: SessionLedger, produced_internals: Dict[str, Any]) -> Dict[str, Any]:
    t, target = wake["actual_start"], wake["execution_target"]
    carried, rejected = [], []
    if session_mode == "same":
        carried = deepcopy(list(ledger.entries.values()))
    else:
        for cid in wake["carryover"]:
            source = fx.by_id.get(cid)
            if cid in produced_internals:
                carried.append(dict(deepcopy(produced_internals[cid]), kind="carryover:internal_result"))
            elif (source and source["type"] in ("human_message", "ambient", "memory", "passive_recall")
                  and source["t"] <= t and source.get("observed_at", source["t"]) <= t
                  and not source.get("ui_only")
                  and (source["type"] != "human_message" or target == "main"
                       or cid in ledger.read_only_sources)):
                carried.append(dict(deepcopy(source), kind="carryover:" + source["type"]))
            else:
                rejected.append({"id": cid, "kind": "carryover", "reason": "not_available_or_not_shared_at_start"})
    internal_ids = [c["id"] for c in carried if c["id"] in produced_internals]
    sel = select_sources(fx, t, internal_ids, target, ledger.read_only_sources)
    sel["excluded"].extend(rejected)
    for c in carried:
        sel["included"].append({"id": c["id"], "kind": c["kind"],
                                "reason": "historical_material_not_asserted_current"})
    session_identity = (
        ledger.session_identity if session_mode == "same"
        else "%s:fresh:%s" % (ledger.session_identity, wake["id"])
    )

    packet = {
        "label": "HYPOTHETICAL_PACKET_built_by_cc_context_lab",
        "warning": "Not a captured CC request. Synthetic lab output only.",
        "policy_id": wake.get("policy_id"),
        "placement": {"rule": wake.get("placement_rule"), "target": target},
        "session_mode": session_mode,
        "session_identity": session_identity,
        "execution_target": target,
        "wake": {
            "candidate_id": wake["id"],
            "trigger_owner_kind": wake["owner_kind"],
            "trigger_owner_detail": wake["owner_detail"],
            "trigger_time": format_time(wake["trigger_time"]),
            "actual_start": format_time(t),
            "scheduled_reasons": sorted(set(wake["reasons"])),
            "turn_busy_at_trigger": wake.get("turn_busy_at_trigger"),
            "chat_active_at_trigger": wake.get("chat_active_at_trigger"),
            "deferred": wake["deferred"],
            "coalesced": wake["coalesced"],
            "coalesced_trigger_ids": wake.get("coalesced_trigger_ids", []),
            "constituents": deepcopy(wake["candidates"]),
            "placement_reason": wake.get("placement_reason"),
        },
        "included": sel["included"],
        "excluded": sel["excluded"],
        "fresh_ambient_blocks": [
            {"id": a["id"], "kind": "ambient", "text": a.get("text", ""),
             "observed_at": format_time(a.get("observed_at", a["t"])),
             "expires_at": format_time(a["expires_at"]) if a.get("expires_at") else None}
            for a in sel["fresh_ambient_blocks"]
        ],
        "memory_items": [{"id": m["id"], "text": m.get("text", "")} for m in sel["memory_items"]],
        "user_text_blocks": [
            {"id": h["id"], "exact_user_text": h["exact_user_text"],
             "origin": h["origin"], "access": h["access"], "wrapper": h["wrapper_metadata"]}
            for h in sel["human_blocks"]
        ],
        "passive_recall_blocks": [
            {"id": r["id"], "supplied_by": r["supplied_by"], "body": r["body"],
             "source_memory_id": r["source_memory_id"]}
            for r in sel["recall_blocks"]
        ],
        "internal_result_blocks": [
            {"id": b["id"], "body": b["body"], "status": b["status"],
             "delivered": False,
             "note": "prior internal-only result; not externally delivered"}
            for b in sel["internal_blocks"]
        ],
        "carried_history_or_carryover": carried,
    }
    return packet

# ---------------------------------------------------------------------------
# Running one (policy, placement, mode)
# ---------------------------------------------------------------------------

def _produced_internals_for(fx: Fixture, wakes: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Assign each internal occurrence to the first ADMITTED wake at/after it."""
    produced = {w["id"]: [] for w in wakes}
    ordered = sorted(wakes, key=lambda w: (w["actual_start"], w["id"]))
    if ordered:
        end = fx.run_end_t if fx.run_end_t is not None else 10 ** 9
        for occ in sorted([o for o in fx.occurrences if o.get("type") == "internal"],
                          key=lambda o: (o["t"], o["id"])):
            for w in ordered:
                if w["actual_start"] >= occ["t"] and w["actual_start"] < end:
                    produced[w["id"]].append(occ["id"])
                    break
    return produced

def run_comparison(fx: Fixture, policy_id: str, placement_id: str,
                   session_mode: str) -> Dict[str, Any]:
    policy = _find(fx.policies, policy_id, "policy")
    placement = _find(fx.placements, placement_id, "placement")
    res = run_placement(fx, policy, placement)

    produced = _produced_internals_for(fx, res["wakes"])
    # Track session ledgers per execution target.
    ledger_main = SessionLedger("main:%s" % fx.shared.get("main_session", "main"))
    ledger_indep = SessionLedger("independent:%s" % fx.shared.get("independent_session", "indep"))
    # Explicit fixture read-only main snapshots for independent runs.
    ro = placement.get("read_only_main_snapshots", [])
    ledger_indep.read_only_sources = list(ro)

    packets, available = [], {}
    for w in res["wakes"]:
        ledger = ledger_main if w["execution_target"] == "main" else ledger_indep
        if session_mode == "fresh":
            ledger.entries.clear()
        pkt = build_packet(fx, dict(w, policy_id=policy_id), session_mode, ledger, available)
        pkt["scripted_outcomes"] = _outcomes_for(fx, w, policy_id)
        # Scripted outcomes occur AFTER packet construction. No current wake
        # can read its own future result; only subsequent starts can select it.
        generated = [dict(deepcopy(fx.internal_by_id(iid)), produced_at=w["actual_start"],
                          producer_wake=w["id"], status="internal_only", delivered=False)
                     for iid in produced.get(w["id"], [])]
        pkt["scripted_produced_results"] = generated
        packets.append(pkt)
        ledger.note_emitted(pkt)
        ledger.note_produced(generated)
        available.update({b["id"]: b for b in generated})

    res["audit"]["session_ledger_ids"] = {
        "main": list(ledger_main.entries), "independent": list(ledger_indep.entries)}
    return {
        "policy_id": policy_id, "placement_id": placement_id,
        "session_mode": session_mode,
        "wakes": res["wakes"], "packets": packets, "audit": res["audit"],
    }

def _find(items, iid, what):
    for it in items:
        if it["id"] == iid:
            return it
    raise KeyError("unknown %s id: %s" % (what, iid))
