#!/usr/bin/env python3
"""Offline checks for request boundaries, not provider behavior."""

import json
from pathlib import Path
import tempfile
import unittest

import prepare_heartbeat_requests as native
from decision_schema import OPTION_INFO, OPTIONS


def example_task():
    return {
        "task_id": "synthetic:one", "task_kind": "heartbeat_activity",
        "state_revision": "synthetic-revision", "observed_state": {"text": "继续读到一半的书"},
        "candidate": {"wake_id": "fixed-0"}, "execution_target": "independent",
        "actual_start": "00:00:00", "selection": {"history": "fresh"},
        "placement_context": {"rule": "independent"},
        "question": {"prompt": "What activity fits this opportunity?", "options": [
            {"option": option, "label": OPTION_INFO[option]["label"],
             "note": OPTION_INFO[option]["note"]} for option in OPTIONS
        ]},
        "expected": "GOLD_SENTINEL", "scripted_outcomes": ["FUTURE_SENTINEL"],
    }


class NativeRequestTests(unittest.TestCase):
    def test_profiles_preserve_same_state_and_options(self):
        task = example_task()
        clef = native.prepare_native(task, "clef-flash")["native_request_body"]
        decisions = native.prepare_native(task, "openai-decisions")["native_request_body"]
        self.assertEqual(clef["state"], json.loads(decisions["input"]))
        question = decisions["questions"][0]
        self.assertEqual(question["name"], "heartbeat_activity")
        self.assertEqual(clef["questions"]["heartbeat_activity"]["criteria"],
                         {c["value"]: c["description"] for c in question["choices"]})
        self.assertEqual(len(question["choices"]), 5)

    def test_binding_and_gold_stay_outside_body(self):
        for profile in native.PROFILES:
            request = native.prepare_native(example_task(), profile)
            body = json.dumps(request["native_request_body"])
            self.assertEqual(request["task_id"], "synthetic:one")
            self.assertEqual(request["state_revision"], "synthetic-revision")
            for text in ("GOLD_SENTINEL", "FUTURE_SENTINEL", "synthetic:one", "synthetic-revision"):
                self.assertNotIn(text, body)
            self.assertEqual(request["status"], "PREPARED_NOT_SENT")

    def test_cli_rejects_duplicates_without_partial_output(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / "tasks.jsonl", Path(temp) / "requests.jsonl"
            source.write_text((json.dumps(example_task()) + "\n") * 2)
            self.assertEqual(native.main([str(source), "--profile", "clef-flash", "--out", str(output)]), 2)
            self.assertFalse(output.exists())

    def test_cli_writes_both_profiles_without_transport(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "tasks.jsonl"
            source.write_text(json.dumps(example_task()) + "\n")
            for profile in native.PROFILES:
                output = Path(temp) / (profile + ".jsonl")
                self.assertEqual(native.main([str(source), "--profile", profile, "--out", str(output)]), 0)
                self.assertEqual(json.loads(output.read_text())["status"], "PREPARED_NOT_SENT")


if __name__ == "__main__":
    unittest.main()
