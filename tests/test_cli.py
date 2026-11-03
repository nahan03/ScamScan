import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import check

from . import samples


def run(args: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = check.main(args)
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name: str, text: str) -> str:
        path = Path(self.tmp.name) / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_prints_a_readable_result_with_the_disclaimer(self):
        code, out, _ = run([self.write("ad.txt", samples.SCAM_FEE), "--no-model"])
        self.assertEqual(code, 0)
        self.assertIn("Risk level: HIGH", out)
        self.assertIn("Red flags:", out)
        self.assertIn("Suggested reply:", out)
        self.assertIn("not a verdict", out)

    def test_output_warns_it_is_not_100_percent_accurate_and_lists_the_checks(self):
        _, out, _ = run([self.write("ad.txt", samples.LEGIT_DETAILED), "--no-model"])
        self.assertIn("NOT 100% ACCURATE", out)
        self.assertIn("does not mean safe", out)
        self.assertIn("Before you reply, verify the employer:", out)
        self.assertIn("Search the company name", out)

    def test_json_output_is_valid(self):
        code, out, _ = run([self.write("ad.txt", samples.LEGIT_DETAILED), "--json", "--no-model"])
        self.assertEqual(code, 0)
        self.assertIn(json.loads(out)["level"], {"low", "medium", "high"})

    def test_missing_file_is_a_clean_error(self):
        code, _, err = run([str(Path(self.tmp.name) / "nope.txt")])
        self.assertEqual(code, 2)
        self.assertIn("Could not read", err)

    def test_empty_file_is_a_clean_error(self):
        code, _, err = run([self.write("empty.txt", "   ")])
        self.assertEqual(code, 2)
        self.assertIn("paste a job ad", err)


if __name__ == "__main__":
    unittest.main()
