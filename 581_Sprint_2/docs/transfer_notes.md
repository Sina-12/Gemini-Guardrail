# Transfer Notes

This file is the short writeup for the transfer-learning part of Sprint 2. It
explains what transferred signal we used, how we added it to each baseline,
and what results we got from those transfer versions.

For the transfer-learning part of Sprint 2, we wanted to add a pretrained signal to both baselines without completely redesigning the models.

We chose pretrained GloVe word embeddings as the transferred signal. We used the `glove-wiki-gigaword-50` vectors through `gensim`.

## Why This Choice Makes Sense

- our dataset is fairly small, so using pretrained vectors is a natural way to add outside information
- GloVe embeddings bring in semantic information that TF-IDF alone does not capture well
- this approach is still simple enough to explain and implement within the sprint
- it lets us keep the basic structure of each baseline while adding a transferred signal

## How We Used The Embeddings

We built separate average embeddings for:

- the source argument text
- the Gemini summary

Then we concatenated those two vectors so the model could still distinguish between the original argument and the generated summary.

### B1+T

For the traditional model, we kept the original TF-IDF features and appended the pretrained GloVe features before fitting logistic regression.

### B2+T

For the neural model, we reduced the TF-IDF features with SVD, appended the pretrained GloVe features, and then trained the MLP on that combined input.

## Current Results

- B1+T: traditional transfer baseline
  - accuracy: `0.625`
  - macro F1: `0.366`

- B2+T: neural transfer baseline
  - accuracy: `0.700`
  - macro F1: `0.275`

## Interpretation

The transferred signal helped the traditional model on macro F1, even though its raw accuracy dropped slightly. That suggests the added embeddings helped it handle the class imbalance a bit better.

For the neural model, the transferred signal did not change the result much. Even without an improvement, we still think the choice is reasonable because it adds a meaningful pretrained semantic representation and gives us a clear comparison point for Sprint 2.

The zero precision and recall scores for some classes are not a bug in the code. They happen because the data is imbalanced and the weaker models tend to overpredict the majority class instead of correctly picking up the rare classes.
