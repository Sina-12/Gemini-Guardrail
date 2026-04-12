from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.pipeline import Pipeline


SRC_DIR = Path(__file__).resolve().parent
SPRINT_DIR = SRC_DIR.parent
DATA_DIR = SPRINT_DIR / "data"
SPRINT1_DATA_DIR = SPRINT_DIR.parent / "581_Sprint_1" / "data"
TRAIN_PATH = SPRINT1_DATA_DIR / "train.csv"
DEV_PATH = SPRINT1_DATA_DIR / "dev.csv"
OUT_PATH = DATA_DIR / "traditional_baseline_predictions.csv"
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


def build_model():
    """
    Build the traditional baseline model used in Sprint 2.

    @param None: This function does not take any parameters.
    @return: An unfitted sklearn Pipeline.
    """
    # We keep the same baseline structure from Sprint 1 so the ensemble is
    # combining the original baseline models rather than a changed version.
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
            (
                "clf",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )
    return model


def main():
    """
    Train and evaluate the traditional Sprint 1 baseline.

    @param None: This function does not take any parameters.
    @return: None. The function prints dev metrics and writes predictions.
    """
    train_df = load_split(TRAIN_PATH)
    dev_df = load_split(DEV_PATH)

    # A standard sparse text baseline: TF-IDF features followed by a linear
    # classifier. This is a strong and interpretable first model for small text
    # datasets like ours.
    model = build_model()

    # We only evaluate on the dev set for Sprint 1 so the test set stays clean.
    model.fit(train_df["model_text"], train_df[TARGET])
    dev_pred = model.predict(dev_df["model_text"])

    acc = accuracy_score(dev_df[TARGET], dev_pred)
    macro_f1 = f1_score(dev_df[TARGET], dev_pred, average="macro")

    print("Traditional baseline: TF-IDF + Logistic Regression")
    print(f"Target annotation label: {TARGET}")
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

    # Saving predictions makes it easier to inspect specific successes and errors.
    out_df = dev_df[["arg_id", TARGET]].copy()
    out_df[f"pred_{TARGET}"] = dev_pred
    out_df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved dev predictions to {OUT_PATH.relative_to(SPRINT_DIR)}")


if __name__ == "__main__":
    main()
