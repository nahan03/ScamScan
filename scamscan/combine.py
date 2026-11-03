"""Blend the rule score and the model probability into one score and level (FR-5)."""

from __future__ import annotations

from .constants import HIGH_THRESHOLD, MEDIUM_THRESHOLD, RULE_WEIGHT
from .rules import RuleResult

LOW, MEDIUM, HIGH = "low", "medium", "high"


def blend(rule_prob: float, model_prob: float | None) -> float:
    """Return a 0-1 score. Without a model the rule probability is used alone."""
    if model_prob is None:
        return rule_prob
    return RULE_WEIGHT * rule_prob + (1 - RULE_WEIGHT) * model_prob


def level_for(prob: float) -> str:
    if prob >= HIGH_THRESHOLD:
        return HIGH
    if prob >= MEDIUM_THRESHOLD:
        return MEDIUM
    return LOW


def combine(rules: RuleResult, model_prob: float | None) -> tuple[int, str]:
    """Return (score 0-100, level). A hard flag forces at least "high" and a matching score."""
    prob = blend(rules.rule_prob, model_prob)
    level = level_for(prob)
    if rules.has_hard:
        level = HIGH
        prob = max(prob, HIGH_THRESHOLD)
    return round(min(max(prob, 0.0), 1.0) * 100), level
