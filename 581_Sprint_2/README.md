# 581 Sprint 2

This README is the quick guide for our Sprint 2 folder. It explains what is in
the folder, how the new files fit together, how to run the scripts, and what
results we got for ensembling and transfer learning.

## Current Sprint 2 Setup

This folder contains both parts of Sprint 2:

- ensembling the original baselines
- adding a transferred pretrained signal to each baseline

Here, `accuracy` refers to the human annotation label for summary quality, not the model evaluation metric.

The original baseline models now live only in `581_Sprint_1/src/`. Sprint 2
reuses those same files directly for ensembling, while the new Sprint 2 code
focuses on ensembling and transfer learning.

## Folder Structure

```text
581_Sprint_2/
  README.md
  data/
    ensemble_predictions.csv
    traditional_transfer_predictions.csv
    rnn_transfer_predictions.csv
  docs/
    ensemble_notes.md
    transfer_notes.md
  src/
    ensemble.py
    embedding_utils.py
    traditional_transfer.py
    rnn_transfer.py
```

## What Each File Is

- `README.md`
  - quick guide to the Sprint 2 folder, how to run the code, and the current results

- `docs/ensemble_notes.md`
  - short writeup for the ensembling part of Sprint 2

- `docs/transfer_notes.md`
  - short writeup for the transfer-learning part of Sprint 2

- `src/ensemble.py`
  - runs the Sprint 2 ensemble setup and reports the `E1` result using the Sprint 1 baseline scripts

- `src/embedding_utils.py`
  - shared helper file for loading GloVe embeddings and building transfer features

- `src/traditional_transfer.py`
  - transfer-learning version of the traditional baseline, used as `B1+T`

- `src/rnn_transfer.py`
  - transfer-learning version of the neural baseline, used as `B2+T`

- `data/ensemble_predictions.csv`
  - saved dev predictions from the current ensemble run

- `data/traditional_transfer_predictions.csv`
  - saved dev predictions from the traditional transfer model

- `data/rnn_transfer_predictions.csv`
  - saved dev predictions from the neural transfer model

## How To Run The Ensemble

From the repository root:

```bash
python 581_Sprint_2/src/ensemble.py
```

The Sprint 2 scripts read the train and dev splits from `581_Sprint_1/data/` and save new Sprint 2 prediction files into `581_Sprint_2/data/`.

Running `ensemble.py` also fits the two Sprint 1 baseline models again as part of the ensemble pipeline and writes the current ensemble predictions to `581_Sprint_2/data/ensemble_predictions.csv`.

Transfer-learning models:

```bash
python 581_Sprint_2/src/traditional_transfer.py
python 581_Sprint_2/src/rnn_transfer.py
```

The first time the transfer scripts run, `gensim` may download the
`glove-wiki-gigaword-50` embeddings if they are not already cached locally.

Optional:

```bash
python 581_Sprint_2/src/ensemble.py --combinations
```

## Current Scope

Per the Sprint 2 instructions and the clarification from the instructor, ensembling and transfer learning are separate pieces.

So far, this folder is set up for:

- B1: traditional baseline
- B2: neural baseline
- E1: ensemble of B1 and B2
- B1+T: traditional baseline with pretrained GloVe features
- B2+T: neural baseline with pretrained GloVe features

## Current Dev Results

- B1: traditional baseline
  - accuracy: `0.650`
  - macro F1: `0.336`

- B2: neural baseline
  - accuracy: `0.700`
  - macro F1: `0.275`

- E1: motivated ensemble
  - accuracy: `0.725`
  - macro F1: `0.372`

- B1+T: traditional transfer baseline
  - accuracy: `0.625`
  - macro F1: `0.366`

- B2+T: neural transfer baseline
  - accuracy: `0.700`
  - macro F1: `0.275`

The best ensemble result came from a manually weighted soft vote that gave more weight to the stronger traditional baseline:

- traditional baseline weight: `0.75`
- neural baseline weight: `0.25`
