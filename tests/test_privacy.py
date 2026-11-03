"""Privacy checks (FR-8, NFR-2): ad text is never stored, written or logged."""

import builtins
import contextlib
import io
import re
import unittest
from pathlib import Path
from unittest import mock

from scamscan.scorer import analyze

from . import samples

ROOT = Path(__file__).resolve().parent.parent
# Code that handles an ad while the app runs. Training and evaluation scripts are separate.
RUNTIME_FILES = [
    *sorted((ROOT / "scamscan").glob("*.py")),
    *sorted((ROOT / "checker").glob("*.py")),
    *sorted((ROOT / "webapp").glob("*.py")),
    ROOT / "check.py",
]
WRITE_PATTERNS = {
    "logging": re.compile(r"\bimport logging\b|\bgetLogger\b"),
    "open for writing": re.compile(r"""open\([^)]*,\s*["'][^"']*[wax+][^"']*["']"""),
    "file write helpers": re.compile(r"\.write_text\(|\.write_bytes\(|\.write\("),
    "joblib dump": re.compile(r"joblib\.dump\("),
}
# Saving the trained model is allowed; it contains no ad text from users.
ALLOWED = {("model.py", "joblib dump")}


class StaticScanTests(unittest.TestCase):
    def test_no_runtime_file_logs_or_writes_to_disk(self):
        problems = []
        for path in RUNTIME_FILES:
            source = path.read_text(encoding="utf-8")
            for name, pattern in WRITE_PATTERNS.items():
                if pattern.search(source) and (path.name, name) not in ALLOWED:
                    problems.append(f"{path.relative_to(ROOT)}: {name}")
        self.assertEqual(problems, [])


class RuntimeTests(unittest.TestCase):
    def test_analyze_touches_no_files_prints_nothing_and_logs_nothing(self):
        out = io.StringIO()
        with (
            mock.patch.object(builtins, "open", side_effect=AssertionError("file access")),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(out),
            self.assertNoLogs(),
        ):
            result = analyze(samples.SCAM_FEE)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(result["level"], "high")


if __name__ == "__main__":
    unittest.main()
