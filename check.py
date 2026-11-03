"""Command-line tool: check a job ad saved in a text file (FR-9).

Usage:
    python check.py ad.txt
    python check.py ad.txt --json
    python check.py - < ad.txt          # read from standard input
    python check.py ad.txt --llm        # Claude explanation if ANTHROPIC_API_KEY is set
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from scamscan.scorer import analyze, default_classifier

DISCLAIMER = "ScamScan shows a risk indicator and reasons. It is not a verdict."


def format_result(result: dict) -> str:
    lines = [f"Risk level: {result['level'].upper()}  (score {result['score']}/100)", ""]
    if result["flags"]:
        lines.append("Red flags:")
        lines += [f"  - {f['label']}: {f['detail']}" for f in result["flags"]]
    else:
        lines.append("Red flags: none found")
    if result["positives"]:
        lines += ["", "Reassuring signs:"] + [f"  + {p['label']}" for p in result["positives"]]
    lines += ["", "Explanation:", f"  {result['summary']}", "", "Suggested reply:"]
    lines += [f"  {line}" for line in result["reply_template"].splitlines()]
    lines += ["", DISCLAIMER]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a job ad for scam warning signs.")
    parser.add_argument("file", help="text file with the ad, or - for standard input")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    parser.add_argument("--llm", action="store_true", help="use Claude for the explanation")
    parser.add_argument("--no-model", action="store_true", help="skip the classifier, rules only")
    args = parser.parse_args(argv)

    try:
        if args.file == "-":
            text = sys.stdin.read()
        else:
            with open(args.file, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
    except OSError as error:
        print(f"Could not read the file: {error.strerror or error}", file=sys.stderr)
        return 2

    classifier = None if args.no_model else default_classifier()
    use_llm = args.llm and bool(os.environ.get("ANTHROPIC_API_KEY"))
    try:
        result = analyze(text, classifier=classifier, use_llm=use_llm)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2) if args.json else format_result(result))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
