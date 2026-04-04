from pathlib import Path

import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline


SRC_DIR = Path(__file__).resolve().parent
SPRINT_DIR = SRC_DIR.parent
DATA_DIR = SPRINT_DIR / "data"
TRAIN_PATH = DATA_DIR / "train.csv"
DEV_PATH = DATA_DIR / "dev.csv"
OUT_PATH = DATA_DIR / "rnn_baseline_predictions.csv"
TARGET = "accuracy"
RANDOM_SEED = 123


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


def main():
    """
    Train and evaluate the simple neural Sprint 1 baseline.

    @param None: This function does not take any parameters.
    @return: None. The function prints dev metrics and writes predictions.
    """
    train_df = load_split(TRAIN_PATH)
    dev_df = load_split(DEV_PATH)

    # This is our simple neural baseline. We keep the same TF-IDF text
    # representation, compress it with SVD, and then train a small MLP.
    model = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    stop_words="english",
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=5000,
                ),
            ),
            ("svd", TruncatedSVD(n_components=100, random_state=RANDOM_SEED)),
            (
                "mlp",
                MLPClassifier(
                    hidden_layer_sizes=(64,),
                    max_iter=400,
                    early_stopping=True,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )

    # We keep the evaluation on dev only so the held-out test set is untouched.
    model.fit(train_df["model_text"], train_df[TARGET])
    dev_pred = model.predict(dev_df["model_text"])

    acc = accuracy_score(dev_df[TARGET], dev_pred)
    macro_f1 = f1_score(dev_df[TARGET], dev_pred, average="macro")

    print("Neural baseline: TF-IDF + TruncatedSVD + MLP")
    print(f"Target label: {TARGET}")
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

    # Saving predictions lets us look at where the neural baseline overpredicts
    # the majority class.
    out_df = dev_df[["arg_id", TARGET]].copy()
    out_df[f"pred_{TARGET}"] = dev_pred
    out_df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved dev predictions to {OUT_PATH.relative_to(SPRINT_DIR)}")


if __name__ == "__main__":
    main()
