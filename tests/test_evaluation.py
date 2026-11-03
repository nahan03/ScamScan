"""Pipeline tests for the UAE-style evaluation. The rows are synthetic and prove only that the
code runs; never report metrics from them."""

import tempfile
import unittest
from pathlib import Path

from scamscan.evaluation import evaluate_labeled, format_comparison, load_labeled

from . import samples


def write_csv(text: str) -> Path:
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="") as handle:
        handle.write(text)
    return Path(handle.name)


class LoadTests(unittest.TestCase):
    def test_skips_unsure_and_blank_rows_and_keeps_row_numbers(self):
        path = write_csv('text,label\n"ad one",scam\n"ad two",unsure\n,legit\n"ad four",LEGIT\n')
        self.addCleanup(path.unlink)
        rows = load_labeled(path)
        self.assertEqual([(n, label) for n, _, label in rows], [(1, 1), (4, 0)])

    def test_unknown_label_is_a_clear_error(self):
        path = write_csv('text,label\n"ad",maybe\n')
        self.addCleanup(path.unlink)
        with self.assertRaises(ValueError) as ctx:
            load_labeled(path)
        self.assertIn("Row 1", str(ctx.exception))

    def test_missing_columns_are_a_clear_error(self):
        path = write_csv("ad,tag\nx,y\n")
        self.addCleanup(path.unlink)
        with self.assertRaises(ValueError):
            load_labeled(path)

    def test_template_file_has_the_right_header(self):
        template = Path(__file__).resolve().parent.parent / "data" / "uae_labeled.template.csv"
        self.assertEqual(template.read_text(encoding="utf-8").strip(), "text,label")


class EvaluateTests(unittest.TestCase):
    rows = (
        (1, samples.SCAM_FEE, 1),
        (2, samples.LEGIT_DETAILED, 0),
        (3, samples.LEGIT_DETAILED, 1),  # deliberately mislabelled to produce a disagreement
    )

    def test_counts_and_agreement(self):
        result = evaluate_labeled(list(self.rows))
        self.assertEqual(result["confusion"], {"tp": 1, "fp": 0, "fn": 1, "tn": 1})
        self.assertAlmostEqual(result["agreement"], 2 / 3)
        self.assertEqual(result["disagreements"], [{"row": 3, "yours": "scam", "level": "low"}])
        self.assertFalse(result["meets_target"])

    def test_no_rows_is_an_error(self):
        with self.assertRaises(ValueError):
            evaluate_labeled([])

    def test_report_never_contains_ad_text(self):
        rules_only = evaluate_labeled(list(self.rows))
        report = format_comparison(rules_only, rules_only)
        self.assertNotIn("registration fee", report)
        self.assertIn("row 3", report)


if __name__ == "__main__":
    unittest.main()
