# Changelog

Semantic versioning. Dates are when the work was done.

## 0.1.0 (2026-11-03) - MVP

Built milestones M1 to M6 of [SDLC-plan.md](SDLC-plan.md).

- M1: repository, CI, tests.
- M2: rules engine (FR-2, FR-3).
- M3: classifier training and evaluation (FR-4, FR-11).
- M4: combined score, redaction, optional Claude explanation, reply template, command-line tool (FR-5 to FR-9).
- M5: Django page with CSRF, a strict Content-Security-Policy and no database (FR-1, FR-10).
- M6: UAE-style evaluation tooling, evaluation report, README with screenshots, Render blueprint.

### Changes from the plan, and why

| Plan said | Now | Reason |
|---|---|---|
| Rules 60%, model 40% | Rules 30%, model 70% | On the public dataset the rules scored below chance (ROC AUC 0.40) because it lacks the patterns they target. See [evaluation.md](evaluation.md). Revisit with the UAE-style set. |
| Logistic regression with balanced class weights | The same, plus sigmoid calibration | Balanced weights inflated probabilities (a clean ad scored "medium"). At the same rule weight, calibration raised combined precision from about 0.42 to 0.87. |
| Rules evaluated on the raw dataset | Rules evaluated with scrubbed `#URL_#` / `#EMAIL_#` markers restored to neutral stand-ins | The dataset removes contact details, so the rules otherwise saw none. |
| Redact emails and phone numbers before any API call | Also redacts links | Links can identify the poster, and `wa.me` links contain phone numbers. |
| Model file "decide at M6" | Committed (about 8 MB) | Small enough, and the deployed app then needs no dataset. |

### Not done yet

- The hand-labelled UAE-style set (30 or more ads). It needs your own labels; the tooling is ready (`eval_uae.py`).
- A live demo link. Deployment config is ready but has not been run on Render.
- Optional "was this right?" feedback button (a "Could" item).
