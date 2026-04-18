"""
Small analysis helper for Sprint 3.

This script compares a baseline prediction file with a stronger model's
prediction file and prints examples that were fixed or broken on the main
`accuracy` task. 
"""

from pathlib import Path

import pandas as pd


PRIMARY_TARGET = "accuracy"
PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE = PROJECT_DIR / "581_Sprint_1" / "data" / "traditional_baseline_predictions.csv"
DEFAULT_BEST = Path(__file__).resolve().parent.parent / "data" / "traditional_mtl_predictions.csv"
DEV_PATH = PROJECT_DIR / "581_Sprint_1" / "data" / "dev.csv"


def load_predictions(path):
    """
    Load one prediction file and standardizes the prediction column name.

    @param path: Path to a prediction CSV file.
    @return: A pandas DataFrame.
    """
    df = pd.read_csv(path)
    pred_cols = [c for c in df.columns if c.startswith("pred_accuracy")]

    if pred_cols:
        df = df.rename(columns={pred_cols[0]: "pred_accuracy"})
    return df


def print_examples(title, df):
    """
    Print a small set of examples for analysis.

    @param title: Section title to print.
    @param df: Input pandas DataFrame.
    @return: None.
    """
    print(f"\n{title}")
    print("-" * len(title))
    if df.empty:
        print("No examples found.")
        return
    
    for _, row in df.head(3).iterrows():
        print(f"arg_id: {row['arg_id']}")
        print(f"gold accuracy: {row[PRIMARY_TARGET]}")
        print(f"baseline pred: {row['pred_accuracy_base']}")
        print(f"best pred: {row['pred_accuracy_best']}")
        print(f"summary snippet: {row['summary'][:350].replace(chr(10), ' ')}")
        print()


def main():
    """
    Compare a baseline model with a stronger model on dev predictions.

    @param None: 
    @return: None. Prints fixed and broken examples.
    """
    baseline_df = load_predictions(DEFAULT_BASELINE)
    best_df = load_predictions(DEFAULT_BEST)
    dev_df = pd.read_csv(DEV_PATH)[["arg_id", "summary", "source_text"]]

    merged = baseline_df.merge(
        best_df[["arg_id", "pred_accuracy"]],
        on="arg_id",
        suffixes=("_base", "_best"),
    )

    merged = merged.merge(dev_df, on="arg_id", how="left")

    fixed = merged[
        (merged["pred_accuracy_base"] != merged[PRIMARY_TARGET])
        & (merged["pred_accuracy_best"] == merged[PRIMARY_TARGET])
    ]
    broken = merged[
        (merged["pred_accuracy_base"] == merged[PRIMARY_TARGET])
        & (merged["pred_accuracy_best"] != merged[PRIMARY_TARGET])
    ]

    print_examples("Fixed examples", fixed)
    print_examples("Broken examples", broken)


if __name__ == "__main__":
    main()
