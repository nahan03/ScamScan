"""Compare ScamScan with your own labels on UAE-style ads.

Usage: python eval_uae.py data/uae_labeled.csv
See data/README.md for the CSV format. Ad text is never printed or saved.
"""

from __future__ import annotations

import sys
from pathlib import Path

from scamscan.evaluation import evaluate_labeled, format_comparison, load_labeled
from scamscan.scorer import default_classifier


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = Path(argv[1])
    if not path.exists():
        print(f"File not found: {path}\nSee data/README.md for the format.")
        return 1
    classifier = default_classifier()
    try:
        rows = load_labeled(path)
        rules_only = evaluate_labeled(rows, classifier=None)
        combined = evaluate_labeled(rows, classifier=classifier)
    except ValueError as error:
        print(error)
        return 2
    print(format_comparison(rules_only, combined))
    if classifier is None:
        print("\nNote: no model file found, so 'Combined' used the rules only.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
