import unittest
from unittest import mock

from scamscan.constants import MAX_CHARS
from scamscan.scorer import analyze, validate

from . import samples

EXPECTED_KEYS = {"level", "score", "flags", "positives", "model_prob", "summary", "reply_template"}


class FakeModel:
    """Stands in for the trained classifier so tests do not depend on a model file."""

    def __init__(self, prob):
        self.prob = prob

    def predict_proba(self, texts):
        return [[1 - self.prob, self.prob] for _ in texts]


class ValidateTests(unittest.TestCase):
    def test_empty_and_blank_input_are_rejected(self):
        for bad in ("", "   \n ", None, 42):
            with self.assertRaises(ValueError):
                validate(bad)

    def test_oversized_input_is_rejected_with_a_clear_message(self):
        with self.assertRaises(ValueError) as ctx:
            validate("a" * (MAX_CHARS + 1))
        self.assertIn("too long", str(ctx.exception))

    def test_input_at_the_limit_is_accepted(self):
        self.assertEqual(len(validate("a" * MAX_CHARS)), MAX_CHARS)


class AnalyzeTests(unittest.TestCase):
    def test_returns_the_documented_contract(self):
        result = analyze(samples.SCAM_FEE)
        self.assertEqual(set(result), EXPECTED_KEYS)
        self.assertIsNone(result["model_prob"])
        self.assertTrue(result["summary"])
        self.assertTrue(result["reply_template"])

    def test_fee_scam_is_high_with_or_without_a_model(self):
        self.assertEqual(analyze(samples.SCAM_FEE)["level"], "high")
        self.assertEqual(analyze(samples.SCAM_FEE, classifier=FakeModel(0.0))["level"], "high")

    def test_legit_ad_is_low_with_a_calm_model(self):
        result = analyze(samples.LEGIT_DETAILED, classifier=FakeModel(0.05))
        self.assertEqual(result["level"], "low")
        self.assertEqual(result["flags"], [])
        self.assertTrue(result["positives"])

    def test_model_probability_is_reported_and_raises_the_score(self):
        calm = analyze(samples.VAGUE_FREE_EMAIL, classifier=FakeModel(0.0))
        alarmed = analyze(samples.VAGUE_FREE_EMAIL, classifier=FakeModel(1.0))
        self.assertEqual(alarmed["model_prob"], 1.0)
        self.assertGreater(alarmed["score"], calm["score"])

    def test_flags_carry_a_label_and_detail(self):
        for flag in analyze(samples.SCAM_FEE)["flags"]:
            self.assertTrue(flag["label"] and flag["detail"])

    def test_invalid_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            analyze("")

    def test_works_without_a_key_or_network_when_llm_is_requested(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            result = analyze(samples.SCAM_FEE, use_llm=True)
        self.assertIn("risk indicator", result["summary"])

    def test_llm_text_is_used_when_the_client_answers(self):
        client = mock.Mock()
        client.messages.create.return_value.content = [mock.Mock(type="text", text="LLM says hi.")]
        result = analyze(samples.SCAM_FEE, use_llm=True, client=client)
        self.assertEqual(result["summary"], "LLM says hi.")
        sent = client.messages.create.call_args.kwargs["messages"][0]["content"]
        self.assertNotIn("+971 50 000 0000", sent)

    def test_api_failure_falls_back_to_the_built_in_text(self):
        client = mock.Mock()
        client.messages.create.side_effect = RuntimeError("boom")
        result = analyze(samples.SCAM_FEE, use_llm=True, client=client)
        self.assertIn("risk indicator", result["summary"])

    def test_reply_template_adapts_to_the_flags(self):
        self.assertIn("own domain", analyze(samples.VAGUE_FREE_EMAIL)["reply_template"])
        self.assertNotIn("own domain", analyze(samples.LEGIT_DETAILED)["reply_template"])


if __name__ == "__main__":
    unittest.main()
