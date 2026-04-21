# 581 Sprint 1

## Folder Structure

```text
581_Sprint_1/
  README.md
  docs/
    reasoned_split.md
  data/
    train.csv
    dev.csv
    test.csv
    traditional_baseline_predictions.csv
    rnn_baseline_predictions.csv
  src/
    spliting_data.py
    traditional_baseline.py
    rnn_baseline.py
```

## What Each File Does

- `README.md`
  Short overview of the Sprint 1 folder, how to run the files, and the final dev scores.

- `docs/reasoned_split.md`
  Explanation of the split logic, leakage prevention, annotator balance, class balance, and why we focused on `accuracy` for Sprint 1.

- `data/train.csv`
  Training split used for the Sprint 1 experiments.

- `data/dev.csv`
  Development split used for model evaluation in Sprint 1.

- `data/test.csv`
  Held-out test split for later work.

- `data/traditional_baseline_predictions.csv`
  Dev-set predictions from the traditional baseline.

- `data/rnn_baseline_predictions.csv`
  Dev-set predictions from the simple neural baseline.

- `src/spliting_data.py`
  Creates the train, dev, and test splits.

- `src/traditional_baseline.py`
  Runs the traditional text-classification baseline using TF-IDF and logistic regression.

- `src/rnn_baseline.py`
  Runs the simple neural baseline using TF-IDF, TruncatedSVD, and an MLP.

## How To Run

From the repository root:

```bash
python 581_Sprint_1/src/spliting_data.py
python 581_Sprint_1/src/traditional_baseline.py
python 581_Sprint_1/src/rnn_baseline.py
```

## Final Dev Scores

- Traditional baseline
  - accuracy: `0.650`
  - macro F1: `0.336`

- Neural baseline
  - accuracy: `0.700`
  - macro F1: `0.275`
