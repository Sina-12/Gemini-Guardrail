"""
Ensemble the original Sprint 1 baselines for Sprint 2.

This script fits the original Sprint 1 baseline models on the Sprint 1 train split and
combines their dev-set predicted probabilities in two ways:

1. Equal-weight soft voting
2. A small manual weight search for two-model ensembles

By default it ensembles the Sprint 1 baseline scripts:
- 581_Sprint_1/src/traditional_baseline.py
- 581_Sprint_1/src/rnn_baseline.py

It can also test every subset combination of the provided models.

In other words, this file is responsible for the E1 part of Sprint 2: taking
the two original Sprint 1 baselines, combining their outputs, and reporting
the best ensemble result on the dev split.
"""

import argparse
import importlib.util
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support


SRC_DIR = Path(__file__).resolve().parent
SPRINT_DIR = SRC_DIR.parent
DATA_DIR = SPRINT_DIR / "data"
SPRINT1_DATA_DIR = SPRINT_DIR.parent / "581_Sprint_1" / "data"
TRAIN_PATH = SPRINT1_DATA_DIR / "train.csv"
DEV_PATH = SPRINT1_DATA_DIR / "dev.csv"
OUT_PATH = DATA_DIR / "ensemble_predictions.csv"
TARGET = "accuracy"
DEFAULT_SCRIPTS = [
    SPRINT_DIR.parent / "581_Sprint_1" / "src" / "traditional_baseline.py",
    SPRINT_DIR.parent / "581_Sprint_1" / "src" / "rnn_baseline.py",
]


def load_models(script_paths):
    """
    Import each script and call its build_model() to get a fresh pipeline.

    @param script_paths: List of Path objects pointing to model scripts.
    @return: List of (name, pipeline) tuples.
    """
    models = []
    for path in script_paths:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "build_model"):
            raise AttributeError(
                f"{path.name} does not expose a build_model() function"
            )
        models.append((path.stem, module.build_model()))
    return models


def load_split(path):
    """
    Load one split and create the text representation used for modeling.

    @param path: Path to a split CSV file.
    @return: A pandas DataFrame with a combined text column for modeling.
    """
    df = pd.read_csv(path)
    df["model_text"] = (
        "SOURCE: "
        + df["source_text"].fillna("").astype(str)
        + "\nSUMMARY: "
        + df["summary"].fillna("").astype(str)
    )
    return df


def print_metrics(name, y_true, y_pred, labels):
    """
    Print accuracy, macro F1, and per-class results for one prediction set.

    @param name: Display name for this model or ensemble.
    @param y_true: True labels.
    @param y_pred: Predicted labels.
    @param labels: Sorted list of class labels.
    @return: Tuple of (accuracy, macro_f1).
    """
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro")
    print(f"\n{'=' * 55}")
    print(f"  {name}")
    print(f"{'=' * 55}")
    print(f"  Dev accuracy : {acc:.3f}")
    print(f"  Dev macro F1 : {macro_f1:.3f}")
    print("  Per-class results:")
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=labels,
        zero_division=0,
    )
    for label, p_score, r_score, f_score in zip(labels, precision, recall, f1):
        print(
            f"    class {label}: "
            f"precision={p_score:.3f}  "
            f"recall={r_score:.3f}  "
            f"f1={f_score:.3f}"
        )
    return acc, macro_f1


def fit_and_predict(models, X_train, y_train, X_dev, y_dev, labels):
    """
    Fit each model and collect predictions, probabilities, and dev scores.

    @param models: List of (name, pipeline) tuples.
    @param X_train: Training text.
    @param y_train: Training labels.
    @param X_dev: Dev text.
    @param y_dev: Dev labels.
    @param labels: Sorted list of label ids.
    @return: Tuple of (model_predictions, model_probabilities, class_order, model_scores).
    """
    model_predictions = []
    model_probabilities = []
    model_scores = []
    class_order = None

    for name, pipeline in models:
        print(f"\nFitting: {name} ...")
        pipeline.fit(X_train, y_train)
        dev_pred = pipeline.predict(X_dev)
        proba = pipeline.predict_proba(X_dev)

        if class_order is None:
            class_order = list(pipeline.classes_)

        model_predictions.append((name, dev_pred))
        model_probabilities.append(proba)
        acc, macro_f1 = print_metrics(name, y_dev, dev_pred, labels)
        model_scores.append((name, acc, macro_f1))

    return model_predictions, model_probabilities, class_order, model_scores


def run_soft_vote(model_probabilities, class_order, weights=None):
    """
    Run a soft-voting ensemble over predicted probabilities.

    @param model_probabilities: List of predicted probability arrays.
    @param class_order: Class order used by the fitted models.
    @param weights: Optional list of model weights.
    @return: List of ensemble predictions.
    """
    if weights is None:
        avg_proba = np.mean(model_probabilities, axis=0)
    else:
        # The weighted version gives a little more influence to models that did
        # better on dev macro F1, since macro F1 is more informative here than
        # raw accuracy alone.
        avg_proba = np.average(model_probabilities, axis=0, weights=weights)
    return [class_order[i] for i in np.argmax(avg_proba, axis=1)]


def search_manual_weights(model_probabilities, class_order, y_dev):
    """
    Search a small set of manual weights for a two-model ensemble.

    @param model_probabilities: List of predicted probability arrays.
    @param class_order: Class order used by the fitted models.
    @param y_dev: Dev labels.
    @return: Tuple of (best_weights, best_pred, best_acc, best_macro_f1).
    """
    if len(model_probabilities) != 2:
        return None, None, None, None

    best_weights = None
    best_pred = None
    best_acc = -1.0
    best_macro_f1 = -1.0

    # We keep the search small and easy to explain. The first weight belongs to
    # the first model listed in the ensemble output.
    for first_weight in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]:
        weights = [first_weight, 1 - first_weight]
        pred = run_soft_vote(model_probabilities, class_order, weights=weights)
        acc = accuracy_score(y_dev, pred)
        macro_f1 = f1_score(y_dev, pred, average="macro")

        # Macro F1 is our main comparison metric here because of class imbalance.
        if macro_f1 > best_macro_f1 or (
            macro_f1 == best_macro_f1 and acc > best_acc
        ):
            best_weights = weights
            best_pred = pred
            best_acc = acc
            best_macro_f1 = macro_f1

    return best_weights, best_pred, best_acc, best_macro_f1


def main():
    """
    Fit the Sprint 1 baselines and evaluate a soft-vote ensemble on dev.

    @param None: Reads optional CLI flags from sys.argv.
    @return: None. Prints metrics and writes dev predictions to disk.
    """
    parser = argparse.ArgumentParser(
        description="Soft-vote ensemble for Sprint 2 baseline models."
    )
    parser.add_argument(
        "scripts",
        nargs="*",
        help="Optional model scripts exposing build_model(); defaults to the two Sprint 1 baseline scripts.",
    )
    parser.add_argument(
        "--combinations",
        action="store_true",
        help="Test every subset combination of size >= 2 instead of one ensemble",
    )
    args = parser.parse_args()

    script_paths = [Path(p).resolve() for p in args.scripts] if args.scripts else DEFAULT_SCRIPTS
    models = load_models(script_paths)

    train_df = load_split(TRAIN_PATH)
    dev_df = load_split(DEV_PATH)

    X_train = train_df["model_text"]
    y_train = train_df[TARGET]
    X_dev = dev_df["model_text"]
    y_dev = dev_df[TARGET]
    labels = sorted(y_dev.unique())

    if args.combinations:
        print(f"Testing all combinations of: {[n for n, _ in models]}")
        summary = []
        for size in range(2, len(models) + 1):
            for subset_indices in itertools.combinations(range(len(models)), size):
                subset_paths = [script_paths[i] for i in subset_indices]
                subset_models = load_models(subset_paths)
                label = " + ".join(n for n, _ in subset_models)

                print(f"\n{'#' * 55}")
                print(f"  Combination: {label}")
                print(f"{'#' * 55}")
                (
                    model_predictions,
                    model_probabilities,
                    class_order,
                    model_scores,
                ) = fit_and_predict(
                    subset_models, X_train, y_train, X_dev, y_dev, labels
                )
                equal_pred = run_soft_vote(model_probabilities, class_order)
                equal_acc, equal_macro_f1 = print_metrics(
                    f"ENSEMBLE ({label}, equal soft vote)", y_dev, equal_pred, labels
                )
                summary.append((f"{label} | equal", equal_acc, equal_macro_f1))

                manual_weights, manual_pred, manual_acc, manual_macro_f1 = search_manual_weights(
                    model_probabilities, class_order, y_dev
                )
                if manual_weights is not None:
                    print(f"\nManual weight search picked: {manual_weights}")
                    print_metrics(
                        f"ENSEMBLE ({label}, manual weighted soft vote)",
                        y_dev,
                        manual_pred,
                        labels,
                    )
                    summary.append((f"{label} | manual", manual_acc, manual_macro_f1))

        print(f"\n{'=' * 55}")
        print("  COMBINATION SUMMARY (sorted by macro F1)")
        print(f"{'=' * 55}")
        for label, acc, macro_f1 in sorted(summary, key=lambda x: x[2], reverse=True):
            print(f"  [{label}]  acc={acc:.3f}  macro_f1={macro_f1:.3f}")
        return

    print(f"Ensemble over {len(models)} method(s): {[n for n, _ in models]}")
    print(f"Target annotation label: {TARGET}")
    print("Scoring methods:")
    print("  1. Equal-weight soft voting on predicted probabilities")
    print("  2. Manual weight search for a two-model ensemble")

    (
        model_predictions,
        model_probabilities,
        class_order,
        model_scores,
    ) = fit_and_predict(
        models, X_train, y_train, X_dev, y_dev, labels
    )

    equal_pred = run_soft_vote(model_probabilities, class_order)
    equal_acc, equal_macro_f1 = print_metrics(
        f"ENSEMBLE (equal soft vote, {len(models)} models)", y_dev, equal_pred, labels
    )

    chosen_name = "equal soft vote"
    chosen_pred = equal_pred
    chosen_acc = equal_acc
    chosen_macro_f1 = equal_macro_f1

    manual_weights, manual_pred, manual_acc, manual_macro_f1 = search_manual_weights(
        model_probabilities, class_order, y_dev
    )
    if manual_weights is not None:
        print(f"\nManual weight search picked: {manual_weights}")
        print_metrics(
            f"ENSEMBLE (manual weighted soft vote, {len(models)} models)",
            y_dev,
            manual_pred,
            labels,
        )
        if manual_macro_f1 > chosen_macro_f1 or (
            manual_macro_f1 == chosen_macro_f1 and manual_acc > chosen_acc
        ):
            chosen_name = f"manual weighted soft vote {manual_weights}"
            chosen_pred = manual_pred
            chosen_acc = manual_acc
            chosen_macro_f1 = manual_macro_f1

    print(f"\nChosen ensemble for saved predictions: {chosen_name}")

    out_df = dev_df[["arg_id", TARGET]].copy()
    out_df[f"pred_{TARGET}"] = chosen_pred
    out_df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved ensemble dev predictions to {OUT_PATH.relative_to(SPRINT_DIR)}")


if __name__ == "__main__":
    main()
