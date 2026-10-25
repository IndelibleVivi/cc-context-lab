#!/usr/bin/env python3
"""Serialize heartbeat tasks to documented native request bodies; never send."""

import argparse
import json
from pathlib import Path
import sys

LAB = Path(__file__).resolve().parents[1] / "experiments" / "companion-input"
sys.path.insert(0, str(LAB))
from decision_schema import OPTIONS, TASK_KIND

PROFILES = {
    "clef-flash": {
        "model": "clef-flash",
        "endpoint_template": "https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/cloudflare/clef-flash",
        "docs": "https://developers.cloudflare.com/workers-ai/models/clef-flash/",
    },
    "openai-decisions": {
        "model": "gpt-6-luna",
        "endpoint_template": "https://api.openai.com/v1/decisions",
        "docs": "https://developers.openai.com/api/docs/guides/decisions",
    },
}


def prepare_native(task, profile):
    """Keep binding metadata outside the native body; use only task evidence."""
    if task.get("task_kind") != TASK_KIND:
        raise ValueError("expected a heartbeat_activity task")
    spec = PROFILES[profile]
    question = task["question"]
    options = question["options"]
    if [option["option"] for option in options] != list(OPTIONS):
        raise ValueError("task options differ from the current heartbeat contract")
    criteria = {
        option["option"]: option["label"] + ". " + option["note"]
        for option in options
    }
    state = {
        "observed_state": task["observed_state"],
        "candidate": task["candidate"],
        "execution_target": task["execution_target"],
        "actual_start": task["actual_start"],
        "history_mode": task["selection"]["history"],
        "placement_context": task["placement_context"],
    }
    if profile == "clef-flash":
        body = {"model": spec["model"], "state": state, "questions": {
            TASK_KIND: {"type": "choice", "instructions": question["prompt"],
                        "criteria": criteria},
        }}
    else:
        body = {"model": spec["model"],
                "input": json.dumps(state, ensure_ascii=False, allow_nan=False),
                "questions": [{
                    "name": TASK_KIND, "type": "choice",
                    "instructions": question["prompt"],
                    "choices": [{"value": key, "description": value}
                                for key, value in criteria.items()],
                }]}
    return {
        "status": "PREPARED_NOT_SENT", "docs_observed_on": "2026-10-13",
        "profile": profile, "endpoint_template": spec["endpoint_template"],
        "source_docs": spec["docs"], "task_id": task["task_id"],
        "state_revision": task["state_revision"], "native_request_body": body,
        "response_adapter": "NOT_IMPLEMENTED; replay accepts the local synthetic answer contract",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", type=Path, help="tasks.jsonl exported by run_decisions.py --prepare-only")
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    out = args.out or Path(".cache/companion-input/decisions") / (args.profile + ".requests.jsonl")
    try:
        rows, seen = [], set()
        for line in args.tasks.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            task = json.loads(line)
            if not isinstance(task, dict):
                raise ValueError("each task must be a JSON object")
            if task["task_id"] in seen:
                raise ValueError("duplicate task_id: " + str(task["task_id"]))
            seen.add(task["task_id"])
            rows.append(prepare_native(task, args.profile))
        if not rows:
            raise ValueError("no tasks to prepare")
        payload = "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows)
        if out.resolve() == args.tasks.resolve():
            raise ValueError("output must differ from source tasks")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("cannot prepare heartbeat requests: " + str(exc), file=sys.stderr)
        return 2
    print(f"PREPARED_NOT_SENT: {len(rows)} {args.profile} bodies -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
