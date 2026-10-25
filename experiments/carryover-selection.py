#!/usr/bin/env python3
"""Offline synthetic checks of the LMC-5 Refined Session Carryover selector.

Loads the *real* `extras/claude_code/refined_session_carryover.py` from a local
public checkout and calls its own selection/truncation functions on synthetic,
non-identifying inputs. It does not copy the algorithm, does not import the
LMC-5 package, does not run the module CLI, and performs no network, model,
filesystem-apply, or real-transcript work.

Usage:
    python3 experiments/carryover-selection.py <lmc-5-checkout>

Exit 0 means the observations below reproduced against the pinned revision.
Exit 0 is NOT a production acceptance of the carryover design; see
docs/forge-upstreams.md and references/forge-upstreams.json for scope.

The script is deliberately tied to the inspected revision
wuxuyun0606-collab/lmc-5@fb3e72c9ee7357c8b17311097b0750082a8a1237. A different
checkout may change behaviour; the assertions name the observed function
contract, so a mismatch shows up as a failing check, not a silent pass.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_REL = Path("extras") / "claude_code" / "refined_session_carryover.py"


def load_upstream_module(checkout: Path):
    """Load the upstream pure-Python module directly, without its package or CLI."""
    module_path = checkout / MODULE_REL
    if not module_path.is_file():
        raise SystemExit(
            f"source not found: {module_path}\n"
            "Pass a local checkout of wuxuyun0606-collab/lmc-5."
        )
    spec = importlib.util.spec_from_file_location("_lmc5_carryover", module_path)
    module = importlib.util.module_from_spec(spec)
    # Python 3.9 dataclasses resolve string annotations via sys.modules[__module__];
    # register before exec so `@dataclass` does not see None.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # module has no top-level side effects beyond defs
    return module


_SEQ = {"n": 0}


def dialogue(kind: str, text: str, **extra) -> dict:
    _SEQ["n"] += 1
    event = {
        "type": kind,
        "message": {"role": kind, "content": text},
        "sessionId": "synthetic-source-session",
        "uuid": f"syn-{kind}-{_SEQ['n']}",
        "parentUuid": None,
    }
    event.update(extra)
    return event


def filler(seed: str, repeats: int) -> str:
    return (seed + " ") * repeats


CHECKS = []


def check(check_id: str, description: str, condition: bool, detail: str) -> None:
    CHECKS.append({"id": check_id, "description": description, "passed": bool(condition), "detail": detail})


def run(module) -> None:
    # C1 — fidelity control: a genuine high-signal memory event is preserved verbatim.
    gold_text = (
        "Remember my preference: I dislike my old nickname, and that identity boundary stands. "
        "Don't forget the promise for next time."
    )
    selected, stats = module.select_refined_events(
        [dialogue("user", "hello there"), dialogue("assistant", gold_text)], tail_events=14
    )
    kept = [module.event_text(event) for event in selected]
    check(
        "C1",
        "high-signal memory event is kept byte-for-byte (fidelity control)",
        gold_text in kept and stats.selected_gold == 1,
        f"selected_gold={stats.selected_gold}, verbatim_present={gold_text in kept}",
    )

    # C2 — long-message middle truncation: compact_text keeps head+tail, drops middle.
    middle = "Boundary: never contact my family without asking."
    long_with_memory = (
        "remember preference identity promise "
        + filler("random engineering prose", 200)
        + middle
        + filler("more trailing prose", 200)
    )
    sanitized = module.compact_text(long_with_memory, 3600)
    check(
        "C2",
        "middle limitation of a long message is dropped by compact_text head+tail window",
        middle not in sanitized and "[refined-carryover: long low-value middle omitted]" in sanitized,
        f"input_len={len(long_with_memory)}, output_len={len(sanitized)}, middle_present={middle in sanitized}",
    )

    # C3 — the same long message still passes the length gate only because it carries
    # >=2 memory hits; without them the >9000-char rule rejects the whole event.
    big_mid_decision = (
        "We agreed the rollout decision is to ship the migration on Friday with a staged canary. "
    ) * 40
    long_decision = filler("opening framing", 200) + big_mid_decision + filler("trailing wrapping", 200)
    classified = module.classify_event(0, dialogue("assistant", long_decision), max_chars=3600)
    check(
        "C3",
        "long (>9000 char) event without >=2 memory hits is rejected whole before truncation",
        classified is None and len(long_decision) > 9000,
        f"input_len={len(long_decision)}, classify={(classified and classified.reason) or None}",
    )

    # C3b — the boundary of the same rule: add two memory hits and the >9000-char event
    # is now kept, but only as its head+tail (the buried decision still does not survive).
    long_with_two_hits = "remember preference " + long_decision
    classified_hits = module.classify_event(0, dialogue("assistant", long_with_two_hits), max_chars=3600)
    buried = "ship the migration on Friday"
    hits_text = module.event_text(classified_hits.event) if classified_hits else None
    kept_hits = classified_hits is not None and buried not in hits_text
    check(
        "C3b",
        "adding >=2 memory hits flips the same long event to kept, but the buried decision is still dropped",
        kept_hits,
        f"input_len={len(long_with_two_hits)}, classify={(classified_hits and classified_hits.reason) or None}, "
        f"buried_present={buried in hits_text if hits_text is not None else None}",
    )

    # C4 — engineering discussion: an important decision outside the tail is kept only
    # if it happens to contain STATE/MEMORY vocabulary; the regex set has no
    # decision/choice/rationale vocabulary of its own. Both variants keep the
    # decision sentence byte-identical; only a STATE prefix is added/removed.
    def discussion(decision_sentence: str):
        events = [dialogue("user", f"engineering note {i}: " + filler("log line noise", 50)) for i in range(20)]
        events.append(dialogue("assistant", decision_sentence))
        events.extend(dialogue("user", f"chatter {i}: " + filler("y", 30)) for i in range(20))
        return events

    decision_sentence = (
        "Decision: we choose Postgres savepoints for Swap instead of table snapshots, "
        "because a single bad row should abort the whole batch."
    )
    state_prefix = "Current task. Next step. "
    plain_decision = decision_sentence
    keyword_decision = state_prefix + decision_sentence
    sel_plain, _ = module.select_refined_events(discussion(plain_decision), tail_events=14)
    sel_keyword, _ = module.select_refined_events(discussion(keyword_decision), tail_events=14)
    plain_kept = any("Postgres savepoints" in module.event_text(e) for e in sel_plain)
    keyword_kept = any("Postgres savepoints" in module.event_text(e) for e in sel_keyword)
    check(
        "C4",
        "a byte-identical decision flips to kept only when a STATE prefix is added",
        plain_kept is False
        and keyword_kept is True
        and decision_sentence in keyword_decision,
        f"plain_decision_kept={plain_kept}, prefixed_decision_kept={keyword_kept}, "
        f"sentence_unchanged={decision_sentence in keyword_decision}",
    )

    # C5 — injection control: exact runtime-injection wrappers never enter the tail.
    injection_events = [
        dialogue("user", "<task-notification>background task finished</task-notification>"),
        dialogue("user", "<system-reminder>injected recall dump</system-reminder>"),
        dialogue("user", "A clean user message."),
        dialogue("assistant", "A clean assistant reply."),
    ]
    sel_inj, _ = module.select_refined_events(injection_events, tail_events=20)
    joined = "\n".join(module.event_text(e) for e in sel_inj)
    check(
        "C5",
        "selection control: task-notification / system-reminder markers are excluded by substring, "
        "not by verified event origin",
        "task-notification" not in joined
        and "system-reminder" not in joined
        and "A clean user message." in joined,
        f"kept_count={len(sel_inj)}",
    )

    # C6 — assistant-first selection gets a synthetic user sentinel so the new
    # transcript still starts with a user turn.
    sel_first, _ = module.select_refined_events(
        [dialogue("assistant", "Remember this relationship promise and continuity memory."),
         dialogue("user", "Hello again.")],
        tail_events=1,
    )
    check(
        "C6",
        "assistant-first carryover is prefixed with a synthetic user sentinel",
        [e["type"] for e in sel_first] == ["user", "assistant", "user"]
        and module.event_text(sel_first[0]).startswith("[refined-carryover:"),
        f"types={[e['type'] for e in sel_first]}",
    )

    # C7 — poison *detection* is a keyword count, not a semantic judgement; a synthetic
    # note merely *about* refusals scores as poison. Fail-closed is a static read of the
    # create_refined_session / main branches (poison_score >= 2), not executed here.
    poison_note = dialogue(
        "user",
        "Postmortem: the last session hit a refusal loop and a policy blocked response; "
        "AUP handling needs a fix. That is not safe content, it is a bug report.",
    )
    score = module.recent_poison_score([poison_note])
    check(
        "C7",
        "poison_score counts policy/refusal vocabulary even in a report that quotes it",
        score >= 2,
        f"poison_score={score}",
    )

    # C8 — tail is a count of candidate events, not raw turns; the budget only
    # removes non-tail candidates, and ensure_user_first runs after the budget sum,
    # so target_tokens is not a hard cap. A tiny target still keeps the tail and the
    # real selector-level estimate exceeds it.
    budget_events = [
        dialogue("user", "remember preference identity promise continuity boundary"),
        dialogue("assistant", filler("clean conversational tail", 40)),
        dialogue("user", filler("more clean tail", 40)),
    ]
    tiny_target = 1
    sel_budget, stats_budget = module.select_refined_events(
        budget_events, target_tokens=tiny_target, tail_events=14
    )
    real_estimate = module.estimate_tokens(sel_budget)
    check(
        "C8",
        "target_tokens is not a hard cap: tail is kept and the real estimate can exceed it",
        len(sel_budget) > 0 and real_estimate > tiny_target,
        f"target_tokens={tiny_target}, kept_events={len(sel_budget)}, "
        f"selector_estimate={real_estimate}, dropped_for_budget={stats_budget.dropped_for_budget}",
    )


def main(argv) -> int:
    if len(argv) != 2:
        print("Usage: python3 experiments/carryover-selection.py <lmc-5-checkout>", file=sys.stderr)
        return 2
    checkout = Path(argv[1])
    module = load_upstream_module(checkout)
    run(module)

    for entry in CHECKS:
        print(f"{entry['id']} {'PASS' if entry['passed'] else 'FAIL'}  {entry['description']}")
        print(f"      {entry['detail']}")

    failed = [entry["id"] for entry in CHECKS if not entry["passed"]]
    if failed:
        print(f"\nFAILED checks: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"all {len(CHECKS)} checks reproduced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
