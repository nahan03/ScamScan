"""Pipeline tests for the classifier.

The data here is synthetic and only proves the pipeline runs. Never report metrics from it.
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scamscan.model import (
    build_text,
    evaluate,
    format_report,
    load_dataset,
    load_model,
    predict_proba,
    restore_placeholders,
    save_model,
    train,
    train_and_evaluate,
)

REAL = "Software engineer responsibilities include building services. Requirements: degree, years of experience."
FAKE = "Urgent hiring! Pay registration fee, earn easy money, contact gmail now guaranteed income."


def synthetic(n: int = 40) -> tuple[list[str], np.ndarray]:
    texts = [f"{REAL} role {i}" if i % 2 else f"{FAKE} offer {i}" for i in range(n)]
    labels = np.array([0 if i % 2 else 1 for i in range(n)])
    return texts, labels


class BuildTextTests(unittest.TestCase):
    def test_joins_present_fields_and_skips_missing(self):
        row = {"title": "Cook", "description": "Cook food", "benefits": float("nan")}
        self.assertEqual(build_text(row), "Cook\nCook food")


class PlaceholderTests(unittest.TestCase):
    def test_restores_url_and_email_markers(self):
        out = restore_placeholders("Apply at #URL_ab12cd# or #EMAIL_0f9e#")
        self.assertIn("https://example.com", out)
        self.assertIn("@example-company.com", out)
        self.assertNotIn("#URL_", out)


class PipelineTests(unittest.TestCase):
    def test_train_predict_save_load(self):
        texts, labels = synthetic()
        model = train(texts, labels)
        self.assertGreater(predict_proba(model, FAKE), predict_proba(model, REAL))
        with tempfile.TemporaryDirectory() as tmp:
            path = save_model(model, Path(tmp) / "m.joblib")
            loaded = load_model(path)
        self.assertAlmostEqual(predict_proba(loaded, FAKE), predict_proba(model, FAKE))

    def test_missing_model_returns_none(self):
        self.assertIsNone(load_model(Path(tempfile.gettempdir()) / "no_such_model.joblib"))

    def test_evaluate_reports_all_methods(self):
        texts, labels = synthetic()
        _, report = train_and_evaluate(texts, labels)
        for key in ("rules", "model", "combined"):
            self.assertEqual(
                set(report[key]), {"roc_auc", "avg_precision", "precision", "recall", "f1"}
            )
        self.assertIn("Combined", format_report(report))

    def test_same_seed_gives_same_report(self):
        texts, labels = synthetic()
        self.assertEqual(train_and_evaluate(texts, labels)[1], train_and_evaluate(texts, labels)[1])

    def test_evaluate_direct(self):
        texts, labels = synthetic()
        report = evaluate(train(texts, labels), texts, labels)
        self.assertEqual(report["n_test"], len(texts))


class LoadDatasetTests(unittest.TestCase):
    def test_load_dataset_drops_empty_rows(self):
        frame = pd.DataFrame({
            "title": ["Cook", None], "description": ["Cook food", None], "fraudulent": [0, 1],
        })
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "d.csv"
            frame.to_csv(csv, index=False)
            texts, labels = load_dataset(csv)
        self.assertEqual(len(texts), 1)
        self.assertEqual(list(labels), [0])

    def test_missing_label_column_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "d.csv"
            pd.DataFrame({"title": ["x"]}).to_csv(csv, index=False)
            with self.assertRaises(ValueError):
                load_dataset(csv)


if __name__ == "__main__":
    unittest.main()
