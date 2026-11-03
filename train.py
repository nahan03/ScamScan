"""Train the classifier from the public dataset and print the evaluation.

Usage: python train.py [path/to/fake_job_postings.csv]
"""

from __future__ import annotations

import sys
from pathlib import Path

from scamscan.constants import MODEL_PATH, ROOT
from scamscan.model import (
    format_report,
    load_dataset,
    save_model,
    train,
    train_and_evaluate,
)

DEFAULT_CSV = ROOT / "data" / "fake_job_postings.csv"


def main(argv: list[str]) -> int:
    csv_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        print(f"Dataset not found: {csv_path}\nSee data/README.md for where to get it.")
        return 1

    texts, labels = load_dataset(csv_path)
    print(f"Loaded {len(texts)} ads ({int(labels.sum())} fraudulent)")

    _, report = train_and_evaluate(texts, labels)
    print(format_report(report))

    # The saved model is trained on all the data; the table above is from the held-out split.
    saved = save_model(train(texts, labels), MODEL_PATH)
    print(f"\nModel saved to {saved}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
