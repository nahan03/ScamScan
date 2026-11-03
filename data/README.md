# Data

Datasets are not committed to git (see `.gitignore`).

## 1. Training dataset (required for `train.py`)

**"Real / Fake Job Posting Prediction"** on Kaggle (based on EMSCAD). Download `fake_job_postings.csv` and save it as `data/fake_job_postings.csv`.
Read the licence and terms on the dataset page, and cite the source in the README.

## 2. Your own UAE-style test set (for `eval_uae.py`)

The public dataset is mostly non-UAE, so the plan asks for a small hand-labelled set of ads that look like the ones people actually receive.

1. Copy `uae_labeled.template.csv` to `uae_labeled.csv`.
2. Add 30 or more ads, one per row, with two columns:
   - `text`: the ad, with **names, email addresses and phone numbers removed** (replace them with words like `[email]`).
   - `label`: `scam`, `legit` or `unsure` (unsure rows are skipped).
3. Label them yourself, before running the tool, so the comparison is fair.
4. Run `python eval_uae.py data/uae_labeled.csv`.

Aim for a mix of both labels. The report shows agreement, precision and recall for the rules alone and for the combined score, and lists the rows that disagree by row number only. It never prints ad text.

Never commit real job ads that contain names, emails or phone numbers.
