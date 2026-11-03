"""Evaluate against your own hand-labelled UAE-style ads (plan section 1.6).

The CSV needs two columns: `text` (the ad, with names, emails and phone numbers removed) and
`label` (`scam` or `legit`; `unsure` rows are skipped). Results never include ad text.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .scorer import analyze

LABELS = {"scam": 1, "legit": 0}
SKIPPED = {"unsure", ""}
TARGET_AGREEMENT = 0.80


def load_labeled(csv_path: Path | str) -> list[tuple[int, str, int]]:
    """Return (row number, text, label) for every usable row. Row numbers start at 1."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"text", "label"} <= set(reader.fieldnames):
            raise ValueError("The CSV needs 'text' and 'label' columns.")
        for number, row in enumerate(reader, 1):
            label = (row.get("label") or "").strip().lower()
            text = (row.get("text") or "").strip()
            if label in SKIPPED or not text:
                continue
            if label not in LABELS:
                raise ValueError(f"Row {number}: label must be 'scam', 'legit' or 'unsure', not '{label}'.")
            rows.append((number, text, LABELS[label]))
    return rows


def _ratio(num: int, den: int) -> float:
    return num / den if den else 0.0


def evaluate_labeled(rows: list[tuple[int, str, int]], classifier=None) -> dict:
    """Score each ad and compare "medium or high" with your label."""
    if not rows:
        raise ValueError("No labelled rows to evaluate.")
    tp = fp = fn = tn = 0
    misses = []
    for number, text, label in rows:
        result = analyze(text, classifier=classifier)
        flagged = result["level"] != "low"
        if flagged and label:
            tp += 1
        elif flagged:
            fp += 1
            misses.append({"row": number, "yours": "legit", "level": result["level"]})
        elif label:
            fn += 1
            misses.append({"row": number, "yours": "scam", "level": result["level"]})
        else:
            tn += 1
    total = len(rows)
    return {
        "n": total,
        "scams": tp + fn,
        "agreement": _ratio(tp + tn, total),
        "precision": _ratio(tp, tp + fp),
        "recall": _ratio(tp, tp + fn),
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "disagreements": misses,
        "meets_target": _ratio(tp + tn, total) >= TARGET_AGREEMENT,
    }


def format_comparison(rules_only: dict, combined: dict) -> str:
    lines = [
        f"Labelled ads: {combined['n']} ({combined['scams']} scam, {combined['n'] - combined['scams']} legit)",
        "",
        "| Method | Agreement | Precision | Recall |",
        "|---|---|---|---|",
    ]
    for name, r in (("Rules only", rules_only), ("Combined", combined)):
        lines.append(f"| {name} | {r['agreement']:.0%} | {r['precision']:.2f} | {r['recall']:.2f} |")
    verdict = "Met by the combined score." if combined["meets_target"] else "Not met by the combined score."
    lines += ["", f"Target: at least {TARGET_AGREEMENT:.0%} agreement. {verdict}"]
    if combined["disagreements"]:
        lines += ["", "Rows where the combined score disagrees with you (row number, your label, our level):"]
        lines += [
            f"  row {m['row']}: you said {m['yours']}, ScamScan said {m['level']}"
            for m in combined["disagreements"]
        ]
    return "\n".join(lines)
