"""analyze(): the single entry point used by the command-line tool and the web page."""

from __future__ import annotations

from functools import lru_cache

from .combine import combine
from .constants import MAX_CHARS, MODEL_PATH
from .explain import VERIFY_STEPS, caveat, fallback_summary, llm_summary, redact, reply_template
from .model import load_model, predict_proba
from .rules import analyze_rules


@lru_cache(maxsize=1)
def default_classifier():
    """Load the trained classifier once. Returns None if no model file exists."""
    return load_model(MODEL_PATH)


def validate(text: str) -> str:
    """Return the cleaned text, or raise ValueError with a message that is safe to show."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Please paste a job ad to check.")
    if len(text) > MAX_CHARS:
        raise ValueError(f"The ad is too long. Please paste at most {MAX_CHARS:,} characters.")
    return text.strip()


def analyze(text: str, classifier=None, use_llm: bool = False, client=None) -> dict:
    """Analyze one job ad. The ad text is never stored or logged.

    Returns level, score (0-100), flags, positives, model_prob (or None), summary,
    reply_template, caveat (what this level does and does not mean) and verify_steps
    (checks that catch what the ad text cannot).
    """
    text = validate(text)
    rules = analyze_rules(text)
    model_prob = predict_proba(classifier, text) if classifier is not None else None
    score, level = combine(rules, model_prob)

    summary = None
    if use_llm:
        summary = llm_summary(redact(text), level, [f.label for f in rules.flags], client=client)
    if summary is None:
        summary = fallback_summary(level, rules.flags, rules.positives, model_prob)

    return {
        "level": level,
        "score": score,
        "flags": [{"code": f.code, "label": f.label, "detail": f.detail} for f in rules.flags],
        "positives": [{"code": p.code, "label": p.label} for p in rules.positives],
        "model_prob": None if model_prob is None else round(model_prob, 3),
        "summary": summary,
        "reply_template": reply_template(rules.codes),
        "caveat": caveat(level),
        "verify_steps": list(VERIFY_STEPS),
    }
