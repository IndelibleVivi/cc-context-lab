"""Typed, single-question decision schema for the companion autonomous-turn lab.

This module defines a *bounded-choice* task shape that this repository owns: a
single question ``heartbeat_activity`` with a fixed, finite option set. It is a
research contract for studying how an explicit limited-choice decision interacts
with an autonomous turn -- it is **not** any provider's wire body, tool schema,
JSON mode, or function-call payload, and it presumes no particular model.

Nothing here talks to a network, a model, a scheduler or a channel. All answers
are supplied by synthetic fixtures and are validated deterministically.

Vocabulary kept deliberately separate:

* answer **status** -- ``ok`` / ``unknown`` / ``refusal`` / ``error``.  A
  refusal, an unknown, or an error is never rewritten into a business option
  such as ``remain_quiet`` or ``insufficient_context``.
* **option** -- one of the five business choices, legal only on an ``ok`` answer.
* **confidence** -- retained verbatim when present; never thresholded here and
  never treated as an accuracy or correctness signal.
* **probabilities** -- optional per-option numbers; validated structurally, not
  scored.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# The one bounded question and its finite option set
# ---------------------------------------------------------------------------

TASK_KIND = "heartbeat_activity"

OPTIONS: Tuple[str, ...] = (
    "remain_quiet",
    "internal_activity",
    "prepare_contact",
    "revisit_later",
    "insufficient_context",
)

#: Short semantics per option.  ``external_delivery`` is false for every option
#: by construction -- even ``prepare_contact`` only yields a draft proposal.
OPTION_INFO: Dict[str, Dict[str, Any]] = {
    "remain_quiet": {
        "label": "remain quiet / no activity this time",
        "hypothetical_intent": "no_activity",
        "releases_activity": False,
        "external_delivery": False,
        "note": "Stay quiet; do not wake activity for this opportunity.",
    },
    "internal_activity": {
        "label": "allow internal activity in a permitted place",
        "hypothetical_intent": "internal_only",
        "releases_activity": True,
        "external_delivery": False,
        "note": "Internal-only work where placement permits; never a message.",
    },
    "prepare_contact": {
        "label": "prepare a contact draft for later human review (never send)",
        "hypothetical_intent": "draft_contact_proposal_for_review",
        "releases_activity": True,
        "external_delivery": False,
        "note": "Produces a DRAFT PROPOSAL only; sending is never granted here.",
    },
    "revisit_later": {
        "label": "suggest re-evaluating later (no automatic timer)",
        "hypothetical_intent": "recommend_reevaluate_later",
        "releases_activity": False,
        "external_delivery": False,
        "note": "A recommendation only; it does NOT schedule any timer or wake.",
    },
    "insufficient_context": {
        "label": "not enough context to choose (business option)",
        "hypothetical_intent": "request_more_context",
        "releases_activity": False,
        "external_delivery": False,
        "note": "A business answer, not an error or a refusal.",
    },
}

# ---------------------------------------------------------------------------
# Answer statuses and error kinds
# ---------------------------------------------------------------------------

STATUS_OK = "ok"
STATUS_UNKNOWN = "unknown"
STATUS_REFUSAL = "refusal"
STATUS_ERROR = "error"
STATUSES: Tuple[str, ...] = (STATUS_OK, STATUS_UNKNOWN, STATUS_REFUSAL, STATUS_ERROR)

#: Fine-grained reasons an ``ok`` answer is downgraded to ``error``, or an
#: ``error`` answer is labelled.  Kept apart from the coarse four statuses.
ERROR_TRANSPORT = "transport_error"
ERROR_UNKNOWN_STATUS = "unknown_status"
ERROR_MISSING_OPTION = "missing_option"
ERROR_INVALID_OPTION = "invalid_option"
ERROR_INVALID_PROBABILITIES = "invalid_probabilities"
ERROR_INVALID_CONFIDENCE = "invalid_confidence"
ERROR_INVALID_PAYLOAD = "invalid_payload"

#: Probability validation outcomes.
PROBS_OK = "probs_ok"
PROBS_NOT_DICT = "probs_not_an_object"
PROBS_KEY_MISMATCH = "probs_missing_or_extra_options"
PROBS_NOT_NUMERIC = "probs_non_numeric_or_bool"
PROBS_NON_FINITE = "probs_non_finite"
PROBS_OUT_OF_RANGE = "probs_out_of_range"
PROBS_SUM_OFF = "probs_sum_not_one"
PROBS_SELECTED_NOT_MAX = "probs_selected_not_a_maximum"

PROB_SUM_TOLERANCE = 1e-6
PROB_RANGE_TOLERANCE = 1e-9


def _is_number(value: Any) -> bool:
    """True only for real numeric scalars (bool is explicitly not a number)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# ---------------------------------------------------------------------------
# Probability validation (structural only; never a correctness score)
# ---------------------------------------------------------------------------

def validate_probabilities(
    probs: Any, options: Tuple[str, ...] = OPTIONS,
) -> Tuple[str, Optional[Dict[str, float]]]:
    """Validate an optional ``probabilities`` object over the option set.

    Returns ``(outcome, normalized_or_None)``.  A complete probabilities object
    must:

    * be an object/dict,
    * contain exactly the option set -- no missing and no extra keys,
    * map every option to a finite numeric non-bool in ``[0, 1]``,
    * sum to 1 (within a small tolerance).

    Missing or partial probabilities are not this function's concern; callers
    decide whether the object is present at all.  This is a structural check,
    not a scoring of answer quality.
    """
    if probs is None:
        return PROBS_NOT_DICT, None
    if not isinstance(probs, dict):
        return PROBS_NOT_DICT, None
    if set(probs.keys()) != set(options):
        return PROBS_KEY_MISMATCH, None
    normalized: Dict[str, float] = {}
    for opt in options:
        value = probs[opt]
        if not _is_number(value):
            return PROBS_NOT_NUMERIC, None
        number = float(value)
        if not math.isfinite(number):
            return PROBS_NON_FINITE, None
        if number < -PROB_RANGE_TOLERANCE or number > 1.0 + PROB_RANGE_TOLERANCE:
            return PROBS_OUT_OF_RANGE, None
        normalized[opt] = number
    total = sum(normalized.values())
    if abs(total - 1.0) > PROB_SUM_TOLERANCE:
        return PROBS_SUM_OFF, None
    return PROBS_OK, normalized


def selected_is_max(
    selected: str, normalized: Dict[str, float],
) -> bool:
    """True when the selected option is one of the maximum-probability options.

    Uses exact equality over the validated values; a tie is allowed.
    """
    if selected not in normalized:
        return False
    top = max(normalized.values())
    return normalized[selected] >= top - PROB_RANGE_TOLERANCE


# ---------------------------------------------------------------------------
# Answer classification
# ---------------------------------------------------------------------------

def classify_answer(
    answer: Any, options: Tuple[str, ...] = OPTIONS,
) -> Dict[str, Any]:
    """Normalize a scripted answer into a status + option + retained fields.

    Contract highlights:

    * ``ok`` requires a legal option; otherwise it becomes ``error``.
    * when ``ok`` carries complete ``probabilities`` they must validate and the
      selected option must be one of the maxima, else ``error``.
    * ``unknown`` / ``refusal`` / ``error`` keep their status; a stray option or
      probabilities on them are recorded but never promoted to a choice.
    * ``confidence`` is retained only when a finite numeric non-bool; a bad
      confidence makes the answer an ``error`` rather than fabricating a value.
    * absent ``confidence`` / ``probabilities`` are left absent -- never invented.
    """
    notes: List[str] = []
    if not isinstance(answer, dict):
        return {
            "status": STATUS_ERROR,
            "error_kind": ERROR_INVALID_PAYLOAD,
            "option": None,
            "confidence": None,
            "probabilities": None,
            "notes": ["answer was not an object"],
        }

    raw_status = answer.get("status")
    option = answer.get("option")
    confidence = answer.get("confidence")
    probs = answer.get("probabilities")

    # Confidence, if present, must be a finite numeric non-bool.
    if confidence is not None and not (
        _is_number(confidence) and math.isfinite(float(confidence))
    ):
        return {
            "status": STATUS_ERROR,
            "error_kind": ERROR_INVALID_CONFIDENCE,
            "option": None,
            "confidence": None,
            "probabilities": None,
            "notes": ["confidence was not a finite numeric non-bool"],
        }

    if raw_status not in STATUSES:
        return {
            "status": STATUS_ERROR,
            "error_kind": ERROR_UNKNOWN_STATUS,
            "option": None,
            "confidence": confidence,
            "probabilities": None,
            "notes": ["status %r is not one of %s" % (raw_status, list(STATUSES))],
        }

    if raw_status == STATUS_OK:
        if option is None:
            return {
                "status": STATUS_ERROR,
                "error_kind": ERROR_MISSING_OPTION,
                "option": None,
                "confidence": confidence,
                "probabilities": None,
                "notes": ["ok answer carried no option"],
            }
        if option not in options:
            return {
                "status": STATUS_ERROR,
                "error_kind": ERROR_INVALID_OPTION,
                "option": None,
                "confidence": confidence,
                "probabilities": None,
                "notes": ["option %r is outside the finite option set" % (option,)],
            }
        normalized_probs: Optional[Dict[str, float]] = None
        if probs is not None:
            outcome, normalized = validate_probabilities(probs, options)
            if outcome != PROBS_OK:
                return {
                    "status": STATUS_ERROR,
                    "error_kind": ERROR_INVALID_PROBABILITIES,
                    "option": None,
                    "confidence": confidence,
                    "probabilities": None,
                    "notes": ["probabilities rejected: %s" % outcome],
                }
            assert normalized is not None
            if not selected_is_max(option, normalized):
                return {
                    "status": STATUS_ERROR,
                    "error_kind": ERROR_INVALID_PROBABILITIES,
                    "option": None,
                    "confidence": confidence,
                    "probabilities": None,
                    "notes": ["selected option is not one of the maxima: %s"
                              % PROBS_SELECTED_NOT_MAX],
                }
            normalized_probs = normalized
        return {
            "status": STATUS_OK,
            "error_kind": None,
            "option": option,
            "confidence": confidence,
            "probabilities": normalized_probs,
            "notes": notes,
        }

    # unknown / refusal / error keep their status.  They must not smuggle a
    # business option, but we record rather than reinterpret it.
    if option is not None:
        notes.append("non-ok status carried an option %r; NOT promoted to a choice"
                     % (option,))
    if probs is not None:
        notes.append("non-ok status carried probabilities; ignored for choice")
    error_kind = None
    if raw_status == STATUS_ERROR:
        error_kind = answer.get("error_kind", ERROR_TRANSPORT)
        if error_kind not in (ERROR_TRANSPORT, ERROR_INVALID_PAYLOAD):
            notes.append("error_kind=%r preserved verbatim" % (error_kind,))
    return {
        "status": raw_status,
        "error_kind": error_kind,
        "option": None,
        "confidence": confidence,
        "probabilities": None,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Hypothetical intent for an admitted choice (never an action)
# ---------------------------------------------------------------------------

def hypothetical_intent(option: str, execution_target: str) -> Dict[str, Any]:
    """Describe what a chosen option *would* mean -- without executing it.

    External delivery is always false.  ``prepare_contact`` yields a draft
    proposal only.  ``revisit_later`` never schedules a timer.
    """
    info = OPTION_INFO[option]
    target_boundary = (
        "independent_session_only" if execution_target == "independent" else "main_thread"
    )
    return {
        "option": option,
        "hypothetical_intent": info["hypothetical_intent"],
        "note": info["note"],
        "writes_main_thread": False,
        "injection_boundary": target_boundary,
        "external_delivery": False,
        "schedules_timer": False,
        "produces_draft_proposal": option == "prepare_contact",
        "releases_activity": bool(info["releases_activity"]),
    }
