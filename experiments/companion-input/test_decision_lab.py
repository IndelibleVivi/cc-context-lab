#!/usr/bin/env python3
"""Integration checks for the typed heartbeat decision prepare/replay lab.

These bind to the real fixtures via the canonical ``run_session`` engine.
"""
import json
from pathlib import Path
import unittest
import tempfile
from unittest import mock

import run_session as rs
import decision_engine as de
import run_decisions as rd

ROOT = Path(__file__).parent
FIXTURES = str(ROOT / "fixtures")
CASES = ROOT / "decision_cases.json"

COMMON = {"fixture": "common_scenario.json", "policy": "P1_fixed_interval",
          "placement": "PL_main_defer", "history": "same"}


def find_task(tasks, candidate):
    for task in tasks:
        if task["candidate"]["wake_id"] == candidate:
            return task
        if candidate in task["candidate"]["coalesced_trigger_ids"]:
            return task
    return None


def bind(task, answer):
    """Attach the consume-entry binding (task_id + revision) to an answer."""
    bound = dict(answer)
    bound["task_id"] = task["task_id"]
    bound["state_revision"] = task["state_revision"]
    return bound


class PrepareChecks(unittest.TestCase):
    def test_blocked_candidate_produces_no_task_but_is_audited(self):
        selection = dict(COMMON, placement="PL_main_skip")
        out = de.prepare(FIXTURES, selection)
        self.assertIsNone(find_task(out["tasks"], "fixed-6"))
        self.assertIn("fixed-6", out["audit"]["skipped_ids"])
        blocked = {b["id"]: b for b in out["audit"]["blocked_candidates"]}
        self.assertEqual(blocked["fixed-6"]["reason"], "skipped_during_chat_active")
        self.assertEqual(blocked["fixed-6"]["fate"], "skipped")

    def test_coalesced_burst_is_one_task_with_provenance(self):
        out = de.prepare(FIXTURES, COMMON)
        task = find_task(out["tasks"], "burst-2100")
        self.assertTrue(task is not None)
        self.assertTrue(task["candidate"]["coalesced"])
        self.assertEqual(task["candidate"]["coalesced_trigger_ids"],
                         ["fixed-3", "fixed-4", "fixed-5", "fixed-6", "fixed-7"])
        self.assertEqual(len([t for t in out["tasks"]
                              if "fixed-6" in t["candidate"]["coalesced_trigger_ids"]]), 1)
        self.assertEqual(len([t for t in out["tasks"]
                              if t["candidate"]["wake_id"] == "fixed-6"]), 0)

    def test_task_carries_no_gold_or_future_fields(self):
        out = de.prepare(FIXTURES, COMMON)
        for task in out["tasks"]:
            blob = json.dumps(task, sort_keys=True)
            for forbidden in ("scripted_outcomes", "scripted_produced_results",
                              "expected", "source_archive", "excluded_source_ids"):
                self.assertNotIn(forbidden, blob)
        # A wake that starts before internal_plan_1 (t=1000) is produced must not
        # see it; only later wakes that legitimately produced it may carry it.
        early = find_task(out["tasks"], "fixed-2")
        self.assertEqual(early["observed_state"]["prior_internal_results"], [])
        later = find_task(out["tasks"], "fixed-8")
        self.assertIn("internal_plan_1",
                      [b["id"] for b in later["observed_state"]["prior_internal_results"]])

    def test_candidate_evidence_is_bound_to_actual_start(self):
        out = de.prepare(FIXTURES, COMMON)
        task = find_task(out["tasks"], "fixed-8")
        mem_ids = [m["id"] for m in task["observed_state"]["memory"]]
        self.assertEqual(mem_ids, ["mem_corr_2"])
        amb_ids = [a["id"] for a in task["observed_state"]["fresh_ambient"]]
        self.assertNotIn("amb_weather_1", amb_ids)
        self.assertIn("amb_env_2", amb_ids)
        self.assertIn("msg_1", [h["id"] for h in task["observed_state"]["human_messages"]])

    def test_superseded_state_is_kept_as_labelled_history_not_current(self):
        out = de.prepare(FIXTURES, COMMON)
        task = find_task(out["tasks"], "fixed-8")
        observed = task["observed_state"]
        # Old weather + corrected taste note were emitted before this wake; they
        # remain available as labelled history, not asserted current.
        hist = {h["id"]: h for h in observed["historical_material"]}
        self.assertIn("amb_weather_1", hist)
        self.assertTrue(hist["amb_weather_1"]["historical"])
        self.assertIn("rain", hist["amb_weather_1"]["text"])
        self.assertIn("mem_taste_1", hist)
        self.assertTrue(hist["mem_taste_1"]["historical"])
        # ... and they are NOT in the current blocks.
        self.assertNotIn("amb_weather_1", [a["id"] for a in observed["fresh_ambient"]])
        self.assertNotIn("mem_taste_1", [m["id"] for m in observed["memory"]])

    def test_future_source_never_appears_in_history(self):
        # A future human message must not leak via historical carryover.
        out = de.prepare(FIXTURES, COMMON)
        early = find_task(out["tasks"], "fixed-2")  # start 00:10:00
        ids = [h["id"] for h in early["observed_state"]["historical_material"]]
        self.assertNotIn("msg_1", ids)  # msg_1 arrives at 00:28:00
        self.assertNotIn("mem_corr_2", ids)

    def test_task_contract_is_not_a_provider_wire_body(self):
        out = de.prepare(FIXTURES, COMMON)
        task = out["tasks"][0]
        self.assertTrue(task["not_a_provider_wire_body"])
        self.assertEqual(task["task_kind"], "heartbeat_activity")


class GateChecks(unittest.TestCase):
    def _task(self, candidate="fixed-8", selection=COMMON):
        out = de.prepare(FIXTURES, selection)
        return find_task(out["tasks"], candidate)

    def test_unbound_answer_is_refused(self):
        task = self._task()
        # A direct caller that forgets to bind is rejected, not silently accepted.
        result = de.consume(
            FIXTURES, task, {"status": "ok", "option": "internal_activity"}, 2400)
        self.assertTrue(result["discarded"])
        self.assertEqual(result["discard_reason"], "answer_missing_task_binding")
        self.assertFalse(result["released"])

    def test_wrong_binding_is_refused(self):
        task = self._task()
        wrong_id = bind(task, {"status": "ok", "option": "internal_activity"})
        wrong_id["task_id"] = "some-other-task"
        result = de.consume(FIXTURES, task, wrong_id, 2400)
        self.assertEqual(result["discard_reason"], "unknown_task_id")
        wrong_rev = bind(task, {"status": "ok", "option": "internal_activity"})
        wrong_rev["state_revision"] = "rev-deadbeefdeadbeef"
        result = de.consume(FIXTURES, task, wrong_rev, 2400)
        self.assertEqual(result["discard_reason"], "bound_revision_mismatch_on_consume")

    def test_active_main_gate_blocks_release(self):
        task = self._task()
        result = de.consume(
            FIXTURES, task, bind(task, {"status": "ok", "option": "internal_activity"}), 2600,
            [{"id": "chat_late", "type": "chat_interval", "t": 2450, "end": 2900}])
        self.assertTrue(result["discarded"])
        self.assertEqual(result["discard_reason"], "chat_active_at_consume")
        self.assertFalse(result["released"])

    def test_target_busy_discards(self):
        task = self._task()
        result = de.consume(
            FIXTURES, task, bind(task, {"status": "ok", "option": "internal_activity"}), 2500,
            [{"id": "busy_late", "type": "busy_interval", "t": 2450, "end": 2550}])
        self.assertEqual(result["discard_reason"], "execution_target_busy_at_consume")
        self.assertFalse(result["released"])

    def test_run_ended_discards(self):
        task = self._task(candidate="fixed-9")
        result = de.consume(FIXTURES, task,
                            bind(task, {"status": "ok", "option": "internal_activity"}), 3010)
        self.assertEqual(result["discard_reason"], "run_ended_before_consume")
        self.assertTrue(result["discarded"])

    def test_late_ambient_expiry_between_start_and_consume_discards(self):
        # start 2400 < expiry 2500 <= consume 2600: a genuine late change.
        task = self._task()
        result = de.consume(
            FIXTURES, task, bind(task, {"status": "ok", "option": "internal_activity"}), 2600,
            [{"id": "amb_expire_env2_late", "type": "ambient_expire", "t": 2500,
              "target": "amb_env_2"}])
        self.assertEqual(result["discard_reason"], "state_revision_changed")
        self.assertNotEqual(result["discard_detail"]["dependency_at_start"],
                            result["discard_detail"]["dependency_at_consume"])

    def test_late_correction_between_start_and_consume_discards(self):
        task = self._task()
        result = de.consume(
            FIXTURES, task, bind(task, {"status": "ok", "option": "internal_activity"}), 2600,
            [{"id": "mem_corr_late", "type": "memory", "t": 2500,
              "corrects": "mem_corr_2",
              "text": "CORRECTION (synthetic): preference is now flat white."}])
        self.assertEqual(result["discard_reason"], "state_revision_changed")

    def test_late_human_message_between_start_and_consume_discards(self):
        task = self._task()
        result = de.consume(
            FIXTURES, task, bind(task, {"status": "ok", "option": "internal_activity"}), 2600,
            [{"id": "msg_late", "type": "human_message", "t": 2500,
              "channel": "telegram", "sender": "user", "sender_time": 2495,
              "reply_target": "chat:dm-42", "attachment": None,
              "body": "actually one more thing (synthetic)"}])
        self.assertEqual(result["discard_reason"], "state_revision_changed")

    def test_unchanged_late_answer_still_releases(self):
        # No dependency change between start (2400) and consume (2600).
        task = self._task()
        result = de.consume(
            FIXTURES, task, bind(task, {"status": "ok", "option": "internal_activity"}), 2600)
        self.assertFalse(result["discarded"])
        self.assertTrue(result["released"])

    def test_late_self_wake_cancellation_between_start_and_consume_discards(self):
        selection = dict(COMMON, policy="P4_self_scheduled_one_shots")
        task = self._task(candidate="sw_afternoon", selection=selection)
        # start 2400 < cancel 2450 <= consume 2500
        result = de.consume(
            FIXTURES, task, bind(task, {"status": "ok", "option": "internal_activity"}), 2500,
            [{"id": "cancel_afternoon_late", "type": "cancel", "t": 2450,
              "target": "sw_afternoon"}])
        self.assertEqual(result["discard_reason"],
                         "constituent_cancelled_before_consume")
        self.assertEqual(result["discard_detail"]["cancelled_constituent"], "sw_afternoon")

    def test_coalesced_constituent_late_cancel_invalidates_whole_task(self):
        # hybrid burst-2400 = [hybrid-tick-periodic-8, sw_afternoon]; cancelling
        # only the self-wake constituent late must still invalidate the task.
        selection = dict(COMMON, policy="P6_hybrid")
        task = self._task(candidate="burst-2400", selection=selection)
        self.assertTrue(task["candidate"]["coalesced"])
        result = de.consume(
            FIXTURES, task, bind(task, {"status": "ok", "option": "internal_activity"}), 2500,
            [{"id": "cancel_afternoon_late", "type": "cancel", "t": 2450,
              "target": "sw_afternoon"}])
        self.assertEqual(result["discard_reason"],
                         "constituent_cancelled_before_consume")

    def test_cancel_before_consume_discards(self):
        selection = dict(COMMON, policy="P4_self_scheduled_one_shots")
        task = self._task(candidate="sw_afternoon", selection=selection)
        result = de.consume(
            FIXTURES, task, bind(task, {"status": "ok", "option": "internal_activity"}), 2400,
            [{"id": "cancel_afternoon", "type": "cancel", "t": 2300,
              "target": "sw_afternoon"}])
        self.assertEqual(result["discard_reason"],
                         "wake_not_reproduced_or_now_blocked")
        self.assertTrue(result["discarded"])

    def test_answer_before_start_discards(self):
        task = self._task()
        result = de.consume(
            FIXTURES, task, bind(task, {"status": "ok", "option": "internal_activity"}), 2300)
        self.assertEqual(result["discard_reason"], "answer_before_actual_start")

    def test_non_ok_answer_never_releases_and_not_a_discard(self):
        task = self._task()
        for answer in ({"status": "unknown"}, {"status": "refusal"}, {"status": "error"}):
            result = de.consume(FIXTURES, task, bind(task, answer), 2400)
            self.assertFalse(result["released"])
            self.assertFalse(result["discarded"])
            self.assertEqual(result["gate"]["gate_result"], "not_released_non_ok_answer")
            self.assertIsNone(result["hypothetical_intent"])

    def test_ok_answer_releases_hypothetical_intent_only(self):
        task = self._task()
        result = de.consume(
            FIXTURES, task, bind(task, {"status": "ok", "option": "internal_activity"}), 2400)
        self.assertFalse(result["discarded"])
        self.assertTrue(result["released"])
        self.assertFalse(result["external_delivery"])
        self.assertFalse(result["hypothetical_intent"]["writes_main_thread"])

    def test_independent_target_does_not_inject_into_main(self):
        selection = dict(COMMON, placement="PL_independent")
        task = self._task(candidate="fixed-4", selection=selection)
        result = de.consume(
            FIXTURES, task, bind(task, {"status": "ok", "option": "internal_activity"}), 1200)
        self.assertEqual(result["hypothetical_intent"]["injection_boundary"],
                         "independent_session_only")
        self.assertFalse(result["hypothetical_intent"]["writes_main_thread"])

    def test_prepare_contact_draft_never_delivers(self):
        task = self._task()
        result = de.consume(
            FIXTURES, task, bind(task, {"status": "ok", "option": "prepare_contact"}), 2400)
        intent = result["hypothetical_intent"]
        self.assertTrue(intent["produces_draft_proposal"])
        self.assertFalse(intent["external_delivery"])


class SuiteChecks(unittest.TestCase):
    def test_all_synthetic_cases_satisfy_expectations(self):
        data, records, violations = rd.run_suite(FIXTURES, str(CASES))
        self.assertEqual(violations, [], msg="violations: %s" % violations)
        self.assertGreaterEqual(len(data["cases"]), 12)

    def test_every_case_answer_is_labelled_synthetic(self):
        data = rs.load_json(str(CASES))
        for case in data["cases"]:
            answer = case.get("answer")
            if answer is not None:
                self.assertTrue(answer.get("synthetic"))
        self.assertIn("SCRIPTED_REPLAY", data["disclaimer"])

    def test_blocked_case_has_no_answer(self):
        data = rs.load_json(str(CASES))
        blocked = [c for c in data["cases"] if c.get("expect", {}).get("blocked")]
        self.assertTrue(blocked)
        for case in blocked:
            self.assertIsNone(case["answer"])

    def test_no_case_scored_as_model_correctness(self):
        data = rs.load_json(str(CASES))
        for case in data["cases"]:
            self.assertNotIn("correct", json.dumps(case.get("expect", {})).lower())

    def test_reports_render_jsonl_tasks_and_markdown(self):
        data, records, violations = rd.run_suite(FIXTURES, str(CASES))
        jsonl = rd._tasks_jsonl(records)
        first = json.loads(jsonl.splitlines()[0])
        self.assertEqual(first["task_kind"], "heartbeat_activity")
        md = rd.render_replay_markdown(data, records, violations)
        self.assertIn("SCRIPTED_REPLAY", md)
        self.assertIn("blocked", md.lower())
        blob = rd.render_replay_json(data, records, violations)
        parsed = json.loads(blob)
        self.assertTrue(parsed["not_a_provider_wire_body"])
        self.assertEqual(parsed["violations"], [])


class EntryPointChecks(unittest.TestCase):
    def test_prepare_only_does_not_read_answers_or_gold(self):
        data = rs.load_json(str(CASES))
        for case in data["cases"]:
            case.pop("answer", None)
            case.pop("expect", None)
        with tempfile.TemporaryDirectory() as temp:
            cases = Path(temp) / "cases.json"
            out = Path(temp) / "output"
            cases.write_text(json.dumps(data))
            with mock.patch.object(de, "consume", side_effect=AssertionError("must not consume")):
                self.assertEqual(rd.main(["--cases", str(cases), "--prepare-only", "--out", str(out)]), 0)
            tasks = [json.loads(line) for line in (out / "tasks.jsonl").read_text().splitlines()]
            self.assertEqual(len(tasks), len({task["task_id"] for task in tasks}))
            self.assertFalse((out / "replay.json").exists())

    def test_failed_check_never_reports_success_or_writes_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "output"
            with mock.patch("subprocess.call", return_value=1):
                self.assertEqual(rd.main(["--check", "--out", str(out)]), 1)
            self.assertFalse(out.exists())

    def test_runner_does_not_overwrite_an_explicit_wrong_binding(self):
        data = rs.load_json(str(CASES))
        case = next(c for c in data["cases"] if c["id"] == "independent_internal_activity")
        case["answer"]["task_id"] = "wrong-task"
        record = rd.run_case(FIXTURES, case)
        self.assertEqual(record["replay"]["discard_reason"], "unknown_task_id")

    def test_removed_constituent_cannot_hide_in_surviving_burst(self):
        selection = dict(COMMON, policy="P6_hybrid")
        raw = de.load_fixture_raw(FIXTURES, "common_scenario.json")
        plan = next(o for o in raw["timeline"] if o["id"] == "sw_afternoon")
        extra = dict(plan, id="extra_self_plan")
        task = find_task(de.prepare(FIXTURES, selection, [extra])["tasks"], "burst-2400")
        self.assertGreaterEqual(len(task["candidate"]["constituents"]), 3)
        result = de.consume(FIXTURES, task, bind(task, {"status": "ok", "option": "internal_activity"}), 2500,
                            [extra, {"id": "cancel_constituent", "type": "cancel", "t": 2300,
                                     "target": "sw_afternoon"}])
        self.assertTrue(result["discarded"])
        self.assertFalse(result["released"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
