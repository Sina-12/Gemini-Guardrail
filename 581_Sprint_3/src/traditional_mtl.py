"""
Traditional multi-task model for Sprint 3.

This file builds a multi-task version of the Sprint 2 traditional transfer
model. The model predicts a joint label made from the primary `accuracy`
annotation and the auxiliary `brevity` annotation and then converts the 
joint prediction back into the main accuracy label for evaluation
"""

from pathlib import Path

import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support

from embedding_utils import (
    AUX_TARGET,
    PRIMARY_TARGET,
    SPRINT1_DATA_DIR,
    build_embedding_features,
    build_joint_labels,
    decode_joint_predictions,
    fit_joint_label_encoder,
    load_embedding_model,
    load_split,
    unpack_joint_predictions,
)


SRC_DIR = Path(__file__).resolve().parent
SPRINT_DIR = SRC_DIR.parent
DATA_DIR = SPRINT_DIR / "data"
TRAIN_PATH = SPRINT1_DATA_DIR / "train.csv"
DEV_PATH = SPRINT1_DATA_DIR / "dev.csv"
OUT_PATH = DATA_DIR / "traditional_mtl_predictions.csv"
RANDOM_SEED = 123


def main():
    """
    Train and evaluate the traditional Sprint 3 multi-task model.

    @param None
    @return: None. The function prints dev metrics and writes predictions.
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

    X_train_tfidf = vectorizer.fit_transform(train_df["model_text"])
    X_dev_tfidf = vectorizer.transform(dev_df["model_text"])

    X_train_emb = build_embedding_features(train_df, embedding_model)
    X_dev_emb = build_embedding_features(dev_df, embedding_model)

    X_train = hstack([X_train_tfidf, csr_matrix(X_train_emb)])
    X_dev = hstack([X_dev_tfidf, csr_matrix(X_dev_emb)])

    model = LogisticRegression(
        max_iter=2000,
        C=2.0,
        class_weight="balanced",
        random_state=RANDOM_SEED,
    )

    model.fit(X_train, train_joint_encoded)
    joint_pred_encoded = model.predict(X_dev)
    joint_pred = decode_joint_predictions(joint_pred_encoded, joint_encoder)
    pred_accuracy, pred_brevity = unpack_joint_predictions(joint_pred)

    acc = accuracy_score(dev_df[PRIMARY_TARGET], pred_accuracy)
    macro_f1 = f1_score(dev_df[PRIMARY_TARGET], pred_accuracy, average="macro")

    print("Traditional multi-task model: TF-IDF + GloVe + Logistic Regression")
    print(f"Primary annotation label: {PRIMARY_TARGET}")
    print(f"Auxiliary annotation label: {AUX_TARGET}")
    print("Multi-task setup: joint accuracy-brevity classes")
    print(f"Dev accuracy: {acc:.3f}")
    print(f"Dev macro F1: {macro_f1:.3f}")
    print("\nPer-class results (primary task only):")
    precision, recall, f1, _ = precision_recall_fscore_support(
        dev_df[PRIMARY_TARGET],
        pred_accuracy,
        labels=sorted(dev_df[PRIMARY_TARGET].unique()),
        zero_division=0,
    )
    for label, p_score, r_score, f_score in zip(
        sorted(dev_df[PRIMARY_TARGET].unique()), precision, recall, f1
    ):
        print(
            f"  class {label}: "
            f"precision={p_score:.3f} "
            f"recall={r_score:.3f} "
            f"f1={f_score:.3f}"
        )

    out_df = dev_df[["arg_id", PRIMARY_TARGET, AUX_TARGET]].copy()
    out_df["pred_joint"] = joint_pred
    out_df[f"pred_{PRIMARY_TARGET}"] = pred_accuracy
    out_df[f"pred_{AUX_TARGET}"] = pred_brevity
    out_df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved dev predictions to {OUT_PATH.relative_to(SPRINT_DIR)}")


if __name__ == "__main__":
    main()
