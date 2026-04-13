"""
Neural transfer-learning baseline for Sprint 2.

This file builds B2+T. It keeps the neural baseline structure, compresses the
TF-IDF features with SVD, adds pretrained GloVe embedding features, trains the
MLP, prints the dev results, and saves the dev predictions.
"""

from pathlib import Path

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.neural_network import MLPClassifier

from embedding_utils import (
    SPRINT1_DATA_DIR,
    TARGET,
    build_embedding_features,
    load_embedding_model,
    load_split,
)


SRC_DIR = Path(__file__).resolve().parent
SPRINT_DIR = SRC_DIR.parent
DATA_DIR = SPRINT_DIR / "data"
TRAIN_PATH = SPRINT1_DATA_DIR / "train.csv"
DEV_PATH = SPRINT1_DATA_DIR / "dev.csv"
OUT_PATH = DATA_DIR / "rnn_transfer_predictions.csv"
RANDOM_SEED = 123


def main():
    """
    Train and evaluate the neural transfer-learning baseline.

    @param None: This function does not take any parameters.
    @return: None. The function prints dev metrics and writes predictions.
    """
    train_df = load_split(TRAIN_PATH)
    dev_df = load_split(DEV_PATH)
    embedding_model = load_embedding_model()

    # Here we keep the baseline TF-IDF signal, compress it with SVD, and then
    # append the transferred GloVe features before training the MLP.
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_features=5000,
    )
    X_train_tfidf = vectorizer.fit_transform(train_df["model_text"])
    X_dev_tfidf = vectorizer.transform(dev_df["model_text"])

    reducer = TruncatedSVD(n_components=50, random_state=RANDOM_SEED)
    X_train_svd = reducer.fit_transform(X_train_tfidf)
    X_dev_svd = reducer.transform(X_dev_tfidf)

    X_train_emb = build_embedding_features(train_df, embedding_model)
    X_dev_emb = build_embedding_features(dev_df, embedding_model)

    X_train = np.hstack([X_train_svd, X_train_emb])
    X_dev = np.hstack([X_dev_svd, X_dev_emb])

    model = MLPClassifier(
        hidden_layer_sizes=(64,),
        max_iter=500,
        early_stopping=True,
        random_state=RANDOM_SEED,
    )
    model.fit(X_train, train_df[TARGET])
    dev_pred = model.predict(X_dev)

    acc = accuracy_score(dev_df[TARGET], dev_pred)
    macro_f1 = f1_score(dev_df[TARGET], dev_pred, average="macro")

    print("Neural transfer baseline: SVD(TF-IDF) + GloVe + MLP")
    print(f"Target annotation label: {TARGET}")
    print(f"Transferred signal: separate GloVe embeddings for source text and summary")
    print(f"Dev accuracy: {acc:.3f}")
    print(f"Dev macro F1: {macro_f1:.3f}")
    print("\nPer-class results:")
    precision, recall, f1, _ = precision_recall_fscore_support(
        dev_df[TARGET],
        dev_pred,
        labels=sorted(dev_df[TARGET].unique()),
        zero_division=0,
    )
    for label, p_score, r_score, f_score in zip(
        sorted(dev_df[TARGET].unique()), precision, recall, f1
    ):
        print(
            f"  class {label}: "
            f"precision={p_score:.3f} "
            f"recall={r_score:.3f} "
            f"f1={f_score:.3f}"
        )

    out_df = dev_df[["arg_id", TARGET]].copy()
    out_df[f"pred_{TARGET}"] = dev_pred
    out_df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved dev predictions to {OUT_PATH.relative_to(SPRINT_DIR)}")


if __name__ == "__main__":
    main()
