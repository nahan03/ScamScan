"""Text classifier for job ads (requirements FR-4 and FR-11).

TF-IDF features + logistic regression give a fraud probability. Balanced class weights
inflate that probability well above the real fraud rate, so it is calibrated (Platt scaling,
3-fold) to make the 0.25 / 0.55 risk thresholds mean what they say. The module also
evaluates rules alone, the model alone and the combined score on a held-out split.
Only load model files you trained yourself: joblib files can run code when loaded.
"""

from __future__ import annotations

import re
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from .constants import MEDIUM_THRESHOLD, MODEL_PATH, RULE_WEIGHT
from .rules import analyze_rules

RANDOM_SEED = 42
TEST_SIZE = 0.2
MODEL_THRESHOLD = 0.5  # probability above which the model alone calls an ad fraud

TEXT_COLUMNS = ("title", "company_profile", "description", "requirements", "benefits")
LABEL_COLUMN = "fraudulent"


def build_text(row: dict) -> str:
    """Join the text fields of one dataset row into a single string."""
    parts = []
    for column in TEXT_COLUMNS:
        value = row.get(column)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return "\n".join(parts)


_URL_PLACEHOLDER_RE = re.compile(r"#URL_[0-9a-f]+#")
_EMAIL_PLACEHOLDER_RE = re.compile(r"#EMAIL_[0-9a-f]+#")


def restore_placeholders(text: str) -> str:
    """Swap the dataset's scrubbed '#URL_..#' and '#EMAIL_..#' markers for neutral stand-ins.

    The public dataset removed real contact details, so the rules would otherwise see "no
    contact" in most ads. The stand-in email is on a company-style domain because the
    real domain is unknown; this means the free-email rule cannot be tested on this data.
    Used for rule evaluation only; the model sees the original text.
    """
    text = _URL_PLACEHOLDER_RE.sub("https://example.com", text)
    return _EMAIL_PLACEHOLDER_RE.sub("contact@example-company.com", text)


def load_dataset(csv_path: Path | str) -> tuple[list[str], np.ndarray]:
    """Read the public CSV and return (texts, labels). Needs pandas (training only)."""
    import pandas as pd

    frame = pd.read_csv(csv_path)
    if LABEL_COLUMN not in frame.columns:
        raise ValueError(f"CSV has no '{LABEL_COLUMN}' column")
    texts = [build_text(row) for row in frame.to_dict("records")]
    labels = frame[LABEL_COLUMN].astype(int).to_numpy()
    keep = [i for i, text in enumerate(texts) if text]
    return [texts[i] for i in keep], labels[keep]


CALIBRATION_FOLDS = 3


def make_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True, stop_words="english", ngram_range=(1, 2),
            min_df=2, max_features=50_000, sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=RANDOM_SEED,
        )),
    ])


def train(texts: list[str], labels: np.ndarray) -> CalibratedClassifierCV:
    """Fit the pipeline with probability calibration. Needs at least 3 ads of each class."""
    model = CalibratedClassifierCV(make_pipeline(), method="sigmoid", cv=CALIBRATION_FOLDS)
    model.fit(texts, labels)
    return model


def save_model(pipeline, path: Path | str = MODEL_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, path)
    return path


def load_model(path: Path | str = MODEL_PATH):
    """Return the saved classifier, or None so the app still works without one."""
    path = Path(path)
    if not path.exists():
        return None
    return joblib.load(path)


def predict_proba(pipeline, text: str) -> float:
    """Fraud probability for one ad."""
    return float(pipeline.predict_proba([text])[0][1])


def _metrics(y_true: np.ndarray, scores: np.ndarray, predicted: np.ndarray) -> dict:
    return {
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "avg_precision": float(average_precision_score(y_true, scores)),
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
    }


def evaluate(pipeline, texts: list[str], labels: np.ndarray) -> dict:
    """Compare rules alone, model alone and combined on held-out data.

    An ad counts as flagged when the model probability is at least MODEL_THRESHOLD,
    or when the rule or combined score reaches MEDIUM_THRESHOLD (or a hard flag fires).
    Rules see the text with dataset placeholders restored (see restore_placeholders).
    """
    labels = np.asarray(labels)
    results = [analyze_rules(restore_placeholders(text)) for text in texts]
    rule_prob = np.array([r.rule_prob for r in results])
    hard = np.array([r.has_hard for r in results])
    model_prob = pipeline.predict_proba(texts)[:, 1]
    combined = RULE_WEIGHT * rule_prob + (1 - RULE_WEIGHT) * model_prob

    return {
        "rules": _metrics(labels, rule_prob, (rule_prob >= MEDIUM_THRESHOLD) | hard),
        "model": _metrics(labels, model_prob, model_prob >= MODEL_THRESHOLD),
        "combined": _metrics(labels, combined, (combined >= MEDIUM_THRESHOLD) | hard),
        "n_test": len(labels),
        "n_fraud": int(labels.sum()),
    }


def train_and_evaluate(
    texts: list[str], labels: np.ndarray
) -> tuple[CalibratedClassifierCV, dict]:
    """Split with a fixed seed, train on the training part, evaluate on the rest."""
    train_x, test_x, train_y, test_y = train_test_split(
        texts, labels, test_size=TEST_SIZE, stratify=labels, random_state=RANDOM_SEED,
    )
    pipeline = train(train_x, train_y)
    return pipeline, evaluate(pipeline, test_x, test_y)


def format_report(report: dict) -> str:
    """Render the evaluation as a Markdown table."""
    lines = [
        f"Held-out test set: {report['n_test']} ads, {report['n_fraud']} fraudulent",
        "",
        "| Method | ROC AUC | Avg precision | Precision | Recall | F1 |",
        "|---|---|---|---|---|---|",
    ]
    for key, name in (("rules", "Rules alone"), ("model", "Model alone"), ("combined", "Combined")):
        m = report[key]
        lines.append(
            f"| {name} | {m['roc_auc']:.3f} | {m['avg_precision']:.3f} | "
            f"{m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} |"
        )
    return "\n".join(lines)
