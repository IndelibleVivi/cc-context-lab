#!/usr/bin/env python3
"""Unit checks for the typed decision schema (classification + probabilities)."""
import unittest

import decision_schema as ds


class ProbabilityChecks(unittest.TestCase):
    def test_complete_valid_probabilities(self):
        probs = {"remain_quiet": 0.1, "internal_activity": 0.5,
                 "prepare_contact": 0.2, "revisit_later": 0.1,
                 "insufficient_context": 0.1}
        outcome, normalized = ds.validate_probabilities(probs)
        self.assertEqual(outcome, ds.PROBS_OK)
        self.assertAlmostEqual(sum(normalized.values()), 1.0)

    def test_missing_and_extra_keys_rejected(self):
        missing = {"remain_quiet": 0.5, "internal_activity": 0.5}
        self.assertEqual(ds.validate_probabilities(missing)[0], ds.PROBS_KEY_MISMATCH)
        extra = {"remain_quiet": 0.1, "internal_activity": 0.1, "prepare_contact": 0.1,
                 "revisit_later": 0.1, "insufficient_context": 0.1, "send_now": 0.5}
        self.assertEqual(ds.validate_probabilities(extra)[0], ds.PROBS_KEY_MISMATCH)

    def test_bool_and_non_numeric_rejected(self):
        probs = {"remain_quiet": True, "internal_activity": 0.3,
                 "prepare_contact": 0.3, "revisit_later": 0.2,
                 "insufficient_context": 0.2}
        self.assertEqual(ds.validate_probabilities(probs)[0], ds.PROBS_NOT_NUMERIC)
        probs["remain_quiet"] = "0.3"
        self.assertEqual(ds.validate_probabilities(probs)[0], ds.PROBS_NOT_NUMERIC)

    def test_non_finite_and_out_of_range_rejected(self):
        base = {"remain_quiet": 0.25, "internal_activity": 0.25,
                "prepare_contact": 0.25, "revisit_later": 0.25,
                "insufficient_context": 0.0}
        bad = dict(base, remain_quiet=float("nan"))
        self.assertEqual(ds.validate_probabilities(bad)[0], ds.PROBS_NON_FINITE)
        bad = dict(base, remain_quiet=1.5)
        self.assertEqual(ds.validate_probabilities(bad)[0], ds.PROBS_OUT_OF_RANGE)

    def test_sum_off_rejected(self):
        probs = {"remain_quiet": 0.3, "internal_activity": 0.3, "prepare_contact": 0.2,
                 "revisit_later": 0.2, "insufficient_context": 0.1}
        self.assertEqual(ds.validate_probabilities(probs)[0], ds.PROBS_SUM_OFF)

    def test_selected_not_max(self):
        normalized = {"remain_quiet": 0.1, "internal_activity": 0.1, "prepare_contact": 0.6,
                      "revisit_later": 0.1, "insufficient_context": 0.1}
        self.assertFalse(ds.selected_is_max("remain_quiet", normalized))
        self.assertTrue(ds.selected_is_max("prepare_contact", normalized))


class ClassificationChecks(unittest.TestCase):
    def test_ok_requires_legal_option(self):
        self.assertEqual(ds.classify_answer(
            {"status": "ok", "option": "internal_activity"})["status"], ds.STATUS_OK)
        bad = ds.classify_answer({"status": "ok", "option": "send_now"})
        self.assertEqual(bad["status"], ds.STATUS_ERROR)
        self.assertEqual(bad["error_kind"], ds.ERROR_INVALID_OPTION)
        missing = ds.classify_answer({"status": "ok"})
        self.assertEqual(missing["error_kind"], ds.ERROR_MISSING_OPTION)

    def test_non_ok_statuses_keep_status_and_drop_option(self):
        for status in ("unknown", "refusal", "error"):
            cls = ds.classify_answer({"status": status, "option": "internal_activity"})
            self.assertEqual(cls["status"], status)
            self.assertIsNone(cls["option"])

    def test_refusal_and_unknown_are_distinct_from_business_options(self):
        refusal = ds.classify_answer({"status": "refusal"})
        unknown = ds.classify_answer({"status": "unknown"})
        self.assertNotEqual(refusal["status"], ds.STATUS_OK)
        self.assertNotEqual(unknown["status"], ds.STATUS_OK)
        self.assertIsNone(refusal["option"])
        self.assertIsNone(unknown["option"])

    def test_error_kind_defaults_to_transport(self):
        cls = ds.classify_answer({"status": "error"})
        self.assertEqual(cls["error_kind"], ds.ERROR_TRANSPORT)

    def test_confidence_retained_but_absent_stays_absent(self):
        keep = ds.classify_answer({"status": "ok", "option": "remain_quiet", "confidence": 0.4})
        self.assertEqual(keep["confidence"], 0.4)
        absent = ds.classify_answer({"status": "ok", "option": "remain_quiet"})
        self.assertIsNone(absent["confidence"])
        bad = ds.classify_answer(
            {"status": "ok", "option": "remain_quiet", "confidence": True})
        self.assertEqual(bad["status"], ds.STATUS_ERROR)
        self.assertEqual(bad["error_kind"], ds.ERROR_INVALID_CONFIDENCE)

    def test_probabilities_absent_stays_absent(self):
        cls = ds.classify_answer({"status": "ok", "option": "remain_quiet"})
        self.assertIsNone(cls["probabilities"])

    def test_invalid_probabilities_downgrade_to_error(self):
        cls = ds.classify_answer({
            "status": "ok", "option": "internal_activity",
            "probabilities": {"remain_quiet": 0.3, "internal_activity": 0.3,
                              "prepare_contact": 0.2, "revisit_later": 0.2,
                              "insufficient_context": 0.1}})
        self.assertEqual(cls["status"], ds.STATUS_ERROR)
        self.assertEqual(cls["error_kind"], ds.ERROR_INVALID_PROBABILITIES)
        self.assertIsNone(cls["option"])

    def test_hypothetical_intent_never_delivers(self):
        for opt in ds.OPTIONS:
            intent = ds.hypothetical_intent(opt, "independent")
            self.assertFalse(intent["external_delivery"])
            self.assertFalse(intent["writes_main_thread"])
        draft = ds.hypothetical_intent("prepare_contact", "main")
        self.assertTrue(draft["produces_draft_proposal"])
        revisit = ds.hypothetical_intent("revisit_later", "main")
        self.assertFalse(revisit["schedules_timer"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
