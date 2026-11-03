"""Shared settings for ScamScan. Change thresholds here, not inside the logic."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "job_scam_model.joblib"

# Largest ad (in characters) the app will accept.
MAX_CHARS = 8000

# Rule scores are summed, then divided by this number to get a 0-1 probability.
RULE_SCORE_DENOMINATOR = 10.0

# Share of the final score that comes from the rules (the model gets the rest).
# Lowered from 0.6 after the first evaluation: the rules scored below chance on the public
# dataset (see docs/evaluation.md). Revisit once a UAE-style test set exists.
RULE_WEIGHT = 0.3

# Score boundaries between low, medium and high risk.
MEDIUM_THRESHOLD = 0.25
HIGH_THRESHOLD = 0.55
