# Reasoned Split

## Why We Did More Than A Simple 80-10-10 Split

We did not want to just randomly split the rows and hope for the best. Our dataset has structure, and that means there are a few ways information could leak across train, dev, and test if we are not careful.

## Leakage Risk From Thread Pairs

Each Reddit thread appears twice in our dataset:

- one successful branch
- one unsuccessful branch

If we split row by row, one version of a thread could end up in train while the other ends up in dev or test. That would be a problem because the two rows still come from the same overall discussion and share a lot of context.

To avoid that, we split by thread number instead of by individual row. This keeps both versions of a thread in the same split.

## Annotator Balance

Another thing we checked was `reviewer_id`. Since the annotations were done by humans, we did not want one split to be mostly from one annotator while another split had a very different mix.

To deal with that, we stratified the thread-level split by `reviewer_id`. This does not make the sets perfectly identical, but it keeps them more balanced than a fully random split.

Our final reviewer distribution is:

- train: `{0: 182, 2: 70, 1: 68}`
- dev: `{0: 22, 1: 10, 2: 8}`
- test: `{0: 24, 1: 8, 2: 8}`

So the reviewer mix is still uneven overall, but the imbalance is not concentrated in just one split.

## Class Distribution

We also checked the label distributions across the splits. The dataset is naturally imbalanced, especially for the `accuracy` label, where class `2` appears much more often than the others.

That imbalance already exists in the original dataset, so the goal of the split was not to make the classes perfectly equal. Instead, the goal was to avoid making one split look very different from the others.

For `accuracy`, the distributions are:

- train: `{2: 243, 1: 67, 0: 10}`
- dev: `{2: 28, 1: 11, 0: 1}`
- test: `{2: 30, 1: 9, 0: 1}`

These are not perfectly matched, but they are close enough that dev and test still look like realistic held-out versions of the same dataset.

## Replicability

We wanted the split to be easy to reproduce later, even if the generated CSV files were lost.

We made the split reproducible by:

- writing the split logic in `581_Sprint_1/src/spliting_data.py`
- using a fixed random seed
- documenting the logic in this file and in the sprint README

So if we needed to regenerate the split later, we could rerun the script and get the same result.

## What We Chose To Model

The dataset includes `sentiment`, `accuracy`, and `brevity`, but for Sprint 1 we focused on `accuracy` as our main prediction target.

We made that choice because `accuracy` feels most central to the project. It directly captures whether the Gemini summary reflects the source argument well. We did not want to spread the sprint too thin by trying to do three separate modeling tasks at once before we even had one clean baseline pipeline.

That does not mean the other labels are unimportant. It just means we treated `accuracy` as the best first task for a focused Sprint 1 submission.

## Summary

Overall, our split is more reasoned than a simple row-level 80-10-10 split because:

- it prevents thread-level leakage
- it pays attention to annotator balance
- it keeps class distributions reasonably similar across splits
- it is reproducible and documented

One thing we also noticed in the baseline results is that some of the lower-frequency classes are hard for the models to predict, and one baseline does not predict every class at all. We do not see that as a good final result, but it is still useful for Sprint 1 because it shows why raw accuracy on its own is not enough here.

That gave us a cleaner starting point for the baseline models.
