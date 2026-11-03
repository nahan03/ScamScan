import unittest

from scamscan.combine import HIGH, LOW, MEDIUM, blend, combine, level_for
from scamscan.constants import HIGH_THRESHOLD, MEDIUM_THRESHOLD, RULE_WEIGHT
from scamscan.rules import Flag, RuleResult


def rules(prob: float, hard: bool = False) -> RuleResult:
    flags = (Flag("fee_request", "Fee", "detail", 6.0, hard=True),) if hard else ()
    return RuleResult(flags, (), prob * 10, prob)


class BlendTests(unittest.TestCase):
    def test_without_a_model_the_rule_probability_is_used_alone(self):
        self.assertEqual(blend(0.4, None), 0.4)

    def test_weights_add_up_to_one(self):
        self.assertAlmostEqual(blend(1.0, 1.0), 1.0)
        self.assertAlmostEqual(blend(0.0, 0.0), 0.0)

    def test_rule_weight_is_applied(self):
        self.assertAlmostEqual(blend(1.0, 0.0), RULE_WEIGHT)
        self.assertAlmostEqual(blend(0.0, 1.0), 1 - RULE_WEIGHT)


class LevelTests(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(level_for(0.0), LOW)
        self.assertEqual(level_for(MEDIUM_THRESHOLD - 0.001), LOW)
        self.assertEqual(level_for(MEDIUM_THRESHOLD), MEDIUM)
        self.assertEqual(level_for(HIGH_THRESHOLD - 0.001), MEDIUM)
        self.assertEqual(level_for(HIGH_THRESHOLD), HIGH)
        self.assertEqual(level_for(1.0), HIGH)


class CombineTests(unittest.TestCase):
    def test_score_is_on_a_0_to_100_scale(self):
        score, level = combine(rules(0.5), None)
        self.assertEqual(score, 50)
        self.assertEqual(level, MEDIUM)

    def test_hard_flag_forces_high_even_with_a_low_model_score(self):
        score, level = combine(rules(0.0, hard=True), 0.0)
        self.assertEqual(level, HIGH)
        self.assertGreaterEqual(score, round(HIGH_THRESHOLD * 100))

    def test_without_a_hard_flag_a_low_score_stays_low(self):
        self.assertEqual(combine(rules(0.0), 0.0), (0, LOW))

    def test_score_never_leaves_the_range(self):
        for rule_prob in (0.0, 0.5, 1.0):
            for model_prob in (None, 0.0, 1.0):
                score, _ = combine(rules(rule_prob), model_prob)
                self.assertTrue(0 <= score <= 100)


if __name__ == "__main__":
    unittest.main()
