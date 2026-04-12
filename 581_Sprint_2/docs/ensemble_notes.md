# Ensemble Notes

This file is the short writeup for the ensembling part of Sprint 2. It explains
what kind of ensemble we used, why we chose it, and what result we got.

For Sprint 2, we ensemble the original baseline models from Sprint 1 rather than changing their core structure.

In this sprint writeup, `accuracy` refers to the human annotation label from our dataset, not model accuracy as an evaluation metric.

We tested two versions of soft voting:

- equal-weight soft voting
- a small manual weight search for the two-model case

All of these methods follow the same basic idea:

- fit each baseline on the Sprint 2 train split
- get predicted probabilities on the dev split
- combine the probabilities across models
- choose the class with the highest combined probability

We chose soft voting because:

- both baselines produce `predict_proba`
- it uses more information than hard voting
- it is simple to explain and reproduce
- it is a reasonable first ensemble before trying more tuned weighting schemes

For the motivated ensemble, we wanted to go one step further than equal weighting. Since the traditional baseline had the stronger macro F1, we tested whether giving it more influence would improve the joint result.

At this stage, the goal is to produce a clean third result from the two baseline models:

- B1: traditional baseline
- B2: neural baseline
- E1: soft-vote ensemble

This keeps the ensembling part separate from transfer learning, which matches the instructor's clarification for Sprint 2.

## Current Result

The best ensemble result came from a manually weighted soft vote:

- traditional baseline weight: `0.75`
- neural baseline weight: `0.25`

That gave us:

- accuracy: `0.725`
- macro F1: `0.372`

This improved on the equal-weight soft vote, so we kept it as our current motivated ensemble result.
