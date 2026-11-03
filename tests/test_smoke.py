import unittest

import scamscan
from scamscan import constants


class SmokeTests(unittest.TestCase):
    def test_package_has_a_semantic_version(self):
        self.assertRegex(scamscan.__version__, r"^\d+\.\d+\.\d+$")

    def test_risk_thresholds_are_ordered(self):
        self.assertTrue(0 < constants.MEDIUM_THRESHOLD < constants.HIGH_THRESHOLD < 1)

    def test_rule_weight_is_a_fraction(self):
        self.assertTrue(0 < constants.RULE_WEIGHT < 1)

    def test_limits_are_positive(self):
        self.assertGreater(constants.MAX_CHARS, 0)
        self.assertGreater(constants.RULE_SCORE_DENOMINATOR, 0)


if __name__ == "__main__":
    unittest.main()
