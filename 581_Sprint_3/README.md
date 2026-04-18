# 581 Sprint 3

In this sprint, our primary task is still predicting the human `accuracy`
annotation label. The auxiliary task is the human `brevity` annotation label.
We use a combinatory class setup, where each model predicts a joint
`accuracy + brevity` label and we then map that prediction back to the primary
`accuracy` label for evaluation.

We chose `brevity` as the secondary task sincei it's closely related to
overall summary quality, goes hand in hand with `accuracy`
and worked better than `sentiment` in a simple comparison with
the traditional multi-task setup.

## Folder Structure

```text
581_Sprint_3/
  README.md
  data/
    ensemble_mtl_predictions.csv
    traditional_mtl_predictions.csv
    rnn_mtl_predictions.csv
  docs/
    multitask_notes.md
    analysis.md
  src/
    ensemble_mtl.py
    embedding_utils.py
    traditional_mtl.py
    rnn_mtl.py
    analyze_models.py
```

## What Each File Is

- `src/ensemble_mtl.py`
  - compares simple ensemble rules that combine the best Sprint 2 and Sprint 3 predictions

- `src/embedding_utils.py`
  - shared helper file for Sprint 3 feature building and joint labels

- `src/traditional_mtl.py`
  - traditional multi-task model built on top of the Sprint 2 transfer setup

- `src/rnn_mtl.py`
  - neural multi-task model built on top of the Sprint 2 transfer setup

- `src/analyze_models.py`
  - helper script for pulling fixed and broken examples from prediction files

- `data/ensemble_mtl_predictions.csv`
  - saved dev predictions from the best simple rule-based Sprint 3 ensemble

- `docs/multitask_notes.md`
  - short writeup explaining the Sprint 3 multi-task setup and results

- `docs/analysis.md`
  - short writeup anlayzing and comparing the different models.

## Dependencies

Required packages:

- `pandas`
- `numpy`
- `scikit-learn`
- `scipy`
- `gensim`

The first time the Sprint 3 models run, `gensim` may download the pretrained
`glove-wiki-gigaword-50` embeddings if they are not already cached locally.

## How To Run

From the repository root:

```bash
python 581_Sprint_3/src/traditional_mtl.py
python 581_Sprint_3/src/rnn_mtl.py
python 581_Sprint_3/src/ensemble_mtl.py
python 581_Sprint_3/src/analyze_models.py
```

## Current Dev Results

- traditional multi-task model
  - accuracy: `0.700`
  - macro F1: `0.421`

- neural multi-task model
  - accuracy: `0.700`
  - macro F1: `0.275`

- confidence-gated Sprint 2/Sprint 3 hybrid
  - accuracy: `0.750`
  - macro F1: `0.415`

The traditional multi-task model is the more promising Sprint 3
result because it improves over the Sprint 1 traditional baseline and over the
Sprint 2 traditional transfer model on both accuracy and macro F1, and it also
beats the Sprint 2 weighted ensemble on macro F1. The confidence-gated hybrid
is the best balanced combined model since it gives the highest accuracy we have seen
so far while still improving over the Sprint 2 weighted ensemble on macro F1 and 
comes just under the traditional multi tasks models macro f1 score.


##### CITATION
ChatGPT. Response to “help brainstorm, debug, and revise project code and documentation for this project.” OpenAI, 18 Apr. 2026, https://chat.openai.com/.