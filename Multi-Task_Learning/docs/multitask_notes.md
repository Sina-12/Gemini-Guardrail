# Multi-task Notes

This file explains the Sprint 3 multi-task setup.

For Sprint 3, we kept the improved Sprint 2 models but we changed the prediction objective so it learns two related labels together rather than just modifying the input. Instead of predicting only the `accuracy` annotation label, each model now predicts a joint label made from:

- `accuracy`
- `brevity`

We chose `brevity` as the auxiliary task since it's another human judgment
of summary quality and it is closely related to predicting accuracy (accuracy as in our annoation criteria not accuracy score). A summary that captures most of the important points concisely is often also more accurate, so the secondary label gives the model another signal about how good the summary is overall.

We preferred `brevity` over `sentiment` for a variety of practical reasons. The
`sentiment` label is much more imbalanced, while `brevity` has a healthier
class spread and gives a more completel joint label space. In a quick comparison with
the traditional multi-task setup, `accuracy + brevity` gave a better macro F1
than `accuracy + sentiment`, so we kept `brevity` as the Sprint 3 auxiliary
task.

We implemented the multi-task objective using combinatory classes. For example,
instead of predicting only `accuracy = 2`, the model predicts a joint label
like `acc_2__brev_1`. After prediction, we map the joint label back to the
main `accuracy` label and evaluate the main task just like we did before.


## Current Results

- traditional multi-task model
  - accuracy: `0.700`
  - macro F1: `0.421`

- neural multi-task model
  - accuracy: `0.700`
  - macro F1: `0.275`

- confidence-gated Sprint 2/Sprint 3 hybrid
  - accuracy: `0.750`
  - macro F1: `0.415`

## Interpretation

The traditional multi-task model is the stronger Sprint 3 result so far. It
improves over the old traditional baseline on both metrics, moving from
`0.650 / 0.336` to `0.700 / 0.421`. It also improves over the Sprint 2
traditional transfer model (`0.625 / 0.366`) on both metrics. This suggests
the auxiliary `brevity` signal is assisting the model in making better decisions on
class `1` without completely just falling back towards the majority class.

The neural multi-task model doesn't improve over the earlier neural results.
Like the Sprint 1 and Sprint 2 neural models, it still seems to heavily
favour the majority class, so the multi-task objective isn't really helping
it break out of that pattern.

We also tried a few simple rule-based combinations of the Sprint 2 weighted
ensemble and the Sprint 3 traditional multi-task model. These are mainly useful
for analysis. Most of them didn't end up givinvg an improvement over the best
existing models on both accuracy and macro F1 at the same time. However, a
confidence-gated hybrid does give a useful tradeoff: it falls back to the
Sprint 2 weighted ensemble on low-margin Sprint 3 cases and reaches
`0.750 / 0.415`. That makes it our strongest and most balanced combined result, even
though the plain tuned traditional multi-task model is still the best pure
macro-F1 result.
