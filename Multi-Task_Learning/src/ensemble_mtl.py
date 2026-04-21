"""
Compare simple ensemble rules that combine Sprint 2 and Sprint 3 predictions.

This script uses saved development predictions rather than retraining old
models. It compares a few small very simple ensemble rules that combine:

- the Sprint 2 weighted ensemble
- the Sprint 3 traditional multi-task model

It also includes a three model vote with the Sprint 1 traditional baseline as
an another point of comparison.
"""

from collections import Counter
from pathlib import Path

import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support

from embedding_utils import (
    SPRINT1_DATA_DIR,
    build_embedding_features,
    build_joint_labels,
    fit_joint_label_encoder,
    load_embedding_model,
    load_split,
)

# Setting path directories for ease of running 
SRC_DIR = Path(__file__).resolve().parent
SPRINT_DIR = SRC_DIR.parent
PROJECT_DIR = SPRINT_DIR.parent
PRIMARY_TARGET = "accuracy"
SPRINT2_ENSEMBLE_PATH = PROJECT_DIR / "581_Sprint_2" / "data" / "ensemble_predictions.csv"
SPRINT3_MTL_PATH = SPRINT_DIR / "data" / "traditional_mtl_predictions.csv"
SPRINT1_BASELINE_PATH = PROJECT_DIR / "581_Sprint_1" / "data" / "traditional_baseline_predictions.csv"
OUT_PATH = SPRINT_DIR / "data" / "ensemble_mtl_predictions.csv"
TRAIN_PATH = SPRINT1_DATA_DIR / "train.csv"
DEV_PATH = SPRINT1_DATA_DIR / "dev.csv"
RANDOM_SEED = 123
CONFIDENCE_MARGIN_THRESHOLD = 0.329


def load_predictions():
    """
    Load the Sprint 2 and Sprint 3 prediction files and merge them by arg_id.

    @param None
    @return: A merged pandas DataFrame.
    """
    sprint2_df = pd.read_csv(SPRINT2_ENSEMBLE_PATH).rename(
        columns={"pred_accuracy": "pred_sprint2"}
    )
    sprint3_df = pd.read_csv(SPRINT3_MTL_PATH).rename(
        columns={"pred_accuracy": "pred_sprint3"}
    )
    merged = sprint2_df.merge(
        sprint3_df[["arg_id", "pred_sprint3", "pred_brevity"]],
        on="arg_id",
        how="inner",
    )
    return merged


def load_sprint3_margin_scores():
    """
    Rebuild the tuned Sprint 3 traditional model and compute dev margins.

    @param None
    @return: DataFrame with arg_id and margin columns.
    """
    train_df = load_split(TRAIN_PATH)
    dev_df = load_split(DEV_PATH)
    embedding_model = load_embedding_model()

    train_joint = build_joint_labels(train_df)
    joint_encoder = fit_joint_label_encoder(train_joint)
    train_joint_encoded = joint_encoder.transform(train_joint)

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_features=5000,
    )
    x_train_tfidf = vectorizer.fit_transform(train_df["model_text"])
    x_dev_tfidf = vectorizer.transform(dev_df["model_text"])

    x_train_emb = build_embedding_features(train_df, embedding_model)
    x_dev_emb = build_embedding_features(dev_df, embedding_model)

    x_train = hstack([x_train_tfidf, csr_matrix(x_train_emb)])
    x_dev = hstack([x_dev_tfidf, csr_matrix(x_dev_emb)])

    model = LogisticRegression(
        max_iter=2000,
        C=2.0,
        class_weight="balanced",
        random_state=RANDOM_SEED,
    )
    model.fit(x_train, train_joint_encoded)
    proba = model.predict_proba(x_dev)
    sorted_proba = proba.copy()
    sorted_proba.sort(axis=1)
    margins = sorted_proba[:, -1] - sorted_proba[:, -2]

    return dev_df[["arg_id"]].assign(sprint3_margin=margins)


def add_baseline_predictions(df):
    """
    Add Sprint 1 traditional baseline predictions for a three-model vote.

    @param df: Merged prediction DataFrame.
    @return: DataFrame with an extra baseline prediction column.
    """
    baseline_df = pd.read_csv(SPRINT1_BASELINE_PATH).rename(
        columns={"pred_accuracy": "pred_baseline"}
    )
    return df.merge(baseline_df[["arg_id", "pred_baseline"]], on="arg_id", how="inner")


def print_metrics(name, y_true, y_pred, labels):
    """
    Print accuracy, macro F1, and results for each class on one prediction set.

    @param name: Display name for the rule being evaluated.
    @param y_true: Gold labels.
    @param y_pred: Predicted labels.
    @param labels: Sorted list of labels.
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


def min_label_rule(df):
    """
    Pick the lower of the Sprint 2 and Sprint 3 predictions.

    @param df: Merged prediction DataFrame.
    @return: List of predictions.
    """
    return df[["pred_sprint2", "pred_sprint3"]].min(axis=1).tolist()


def brevity_gate_rule(df):
    """
    Use the Sprint 3 prediction only when predicted brevity is low.

    @param df: Merged prediction DataFrame.
    @return: List of predictions.
    """
    preds = []
    for pred_s2, pred_s3, pred_brevity in zip(
        df["pred_sprint2"], df["pred_sprint3"], df["pred_brevity"]
    ):
        if pred_s2 != pred_s3 and pred_brevity <= 1:
            preds.append(pred_s3)
        else:
            preds.append(pred_s2)
    return preds


def confidence_gate_rule(df):
    """
    Use Sprint 3 when its joint label margin is high, otherwise use Sprint 2.

    @param df: Merged prediction DataFrame with Sprint 3 margin scores.
    @return: List of predictions.
    """
    preds = []
    for pred_s2, pred_s3, margin in zip(
        df["pred_sprint2"], df["pred_sprint3"], df["sprint3_margin"]
    ):
        if margin >= CONFIDENCE_MARGIN_THRESHOLD:
            preds.append(pred_s3)
        else:
            preds.append(pred_s2)
    return preds


def majority_vote_rule(df):
    """
    Combine the baseline, Sprint 2 ensemble, and Sprint 3 MTL by vote.

    @param df: Merged prediction DataFrame with the baseline column included.
    @return: List of predictions.
    """
    preds = []
    for pred_b1, pred_s2, pred_s3 in zip(
        df["pred_baseline"], df["pred_sprint2"], df["pred_sprint3"]
    ):
        counts = Counter([pred_b1, pred_s2, pred_s3])
        top_count = max(counts.values())
        top_labels = sorted(
            [label for label, count in counts.items() if count == top_count]
        )
        preds.append(top_labels[0])
    return preds


def main():
    """
    Evaluate simple ensemble rules across the best earlier models.

    @param None
    @return: None. Prints metrics and writes the best rule's predictions.
    """
    df = load_predictions().merge(load_sprint3_margin_scores(), on="arg_id", how="inner")
    y_true = df[PRIMARY_TARGET]
    labels = sorted(y_true.unique())

    print("Comparing simple Sprint 3 ensemble rules")
    print(f"Primary annotation label: {PRIMARY_TARGET}")
    print("Models being combined:")
    print("  - Sprint 2 weighted ensemble")
    print("  - Sprint 3 traditional multi-task model")

    rule_results = []

    sprint2_pred = df["pred_sprint2"].tolist()
    acc, macro_f1 = print_metrics("Sprint 2 ensemble only", y_true, sprint2_pred, labels)
    rule_results.append(("sprint2_only", sprint2_pred, acc, macro_f1))

    sprint3_pred = df["pred_sprint3"].tolist()
    acc, macro_f1 = print_metrics("Sprint 3 MTL only", y_true, sprint3_pred, labels)
    rule_results.append(("sprint3_only", sprint3_pred, acc, macro_f1))

    min_pred = min_label_rule(df)
    acc, macro_f1 = print_metrics("Min-label rule", y_true, min_pred, labels)
    rule_results.append(("min_label", min_pred, acc, macro_f1))

    brevity_pred = brevity_gate_rule(df)
    acc, macro_f1 = print_metrics("Brevity-gate rule", y_true, brevity_pred, labels)
    rule_results.append(("brevity_gate", brevity_pred, acc, macro_f1))

    confidence_pred = confidence_gate_rule(df)
    acc, macro_f1 = print_metrics(
        "Confidence-gate rule",
        y_true,
        confidence_pred,
        labels,
    )
    rule_results.append(("confidence_gate", confidence_pred, acc, macro_f1))

    df_three = add_baseline_predictions(df)
    majority_pred = majority_vote_rule(df_three)
    acc, macro_f1 = print_metrics("Three-model majority vote", y_true, majority_pred, labels)
    rule_results.append(("majority_vote", majority_pred, acc, macro_f1))

    best_name, best_pred, best_acc, best_macro_f1 = max(
        rule_results, key=lambda item: (item[3], item[2])
    )

    print(f"\nBest rule by macro F1: {best_name}")
    print(f"Best dev accuracy: {best_acc:.3f}")
    print(f"Best dev macro F1: {best_macro_f1:.3f}")

    out_df = df[["arg_id", PRIMARY_TARGET]].copy()
    out_df["pred_accuracy"] = best_pred
    out_df["selected_rule"] = best_name
    out_df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved best dev predictions to {OUT_PATH.relative_to(SPRINT_DIR)}")


if __name__ == "__main__":
    main()
