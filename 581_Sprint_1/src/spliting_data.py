from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


RANDOM_SEED = 123
SRC_DIR = Path(__file__).resolve().parent
SPRINT_DIR = SRC_DIR.parent
DATA_DIR = SPRINT_DIR / "data"
DATA_PATH = SPRINT_DIR.parent / "data" / "full_annotations_with_source_text.csv"


def load_data():
    """
    Load the annotated summary dataset and add thread metadata.

    @param None: This function does not take any parameters.
    @return: A pandas DataFrame containing the annotated dataset with
        extracted thread numbers and branch variants.
    """
    df = pd.read_csv(DATA_PATH, encoding="latin1")
    df["arg_id"] = df["arg_id"].astype(str)
    df["thread_num"] = df["arg_id"].str.extract(r"(\d+)").astype(int)
    df["variant"] = df["arg_id"].str.extract(r"_([su])$")
    return df


def build_thread_frame(df):
    """
    Build a thread-level frame for splitting.

    @param df: The full annotated dataset as a pandas DataFrame.
    @return: A thread-level DataFrame with one row per thread.

    We split by thread number rather than row so that the successful and
    unsuccessful versions of the same Reddit thread never land in different
    datasets.
    """
    thread_df = (
        df.groupby("thread_num", as_index=False)
        .agg(reviewer_id=("reviewer_id", "first"))
        .sort_values("thread_num")
        .reset_index(drop=True)
    )
    return thread_df


def print_split_summary(name, split_df):
    """
    Print a small summary so the split is easy to inspect and document.

    @param name: The name of the split being summarized.
    @param split_df: A pandas DataFrame for one split.
    @return: None. The function only prints summary information.
    """
    print(
        f"{name}: {len(split_df)} rows | "
        f"{split_df['thread_num'].nunique()} threads | "
        f"reviewers {split_df['reviewer_id'].value_counts().to_dict()}"
    )
    print(f"{name} sentiment: {split_df['sentiment'].value_counts().to_dict()}")
    print(f"{name} accuracy:  {split_df['accuracy'].value_counts().to_dict()}")
    print(f"{name} brevity:   {split_df['brevity'].value_counts().to_dict()}")
    print("---")


def main():
    """
    Create reproducible train, dev, and test splits for Sprint 1.

    @param None: This function does not take any parameters.
    @return: None. The function writes CSV files to disk and prints summaries.
    """
    DATA_DIR.mkdir(exist_ok=True)

    df = load_data()
    thread_df = build_thread_frame(df)

    # We stratify by reviewer so the three splits are not dominated by
    # annotations from just one person.
    train_threads, temp_threads = train_test_split(
        thread_df,
        train_size=0.8,
        random_state=RANDOM_SEED,
        stratify=thread_df["reviewer_id"],
    )

    # The remaining 20% is divided evenly into dev and test.
    dev_threads, test_threads = train_test_split(
        temp_threads,
        train_size=0.5,
        random_state=RANDOM_SEED,
        stratify=temp_threads["reviewer_id"],
    )

    train_ids = set(train_threads["thread_num"])
    dev_ids = set(dev_threads["thread_num"])
    test_ids = set(test_threads["thread_num"])

    if train_ids & dev_ids or train_ids & test_ids or dev_ids & test_ids:
        raise ValueError("Thread leakage detected across splits.")

    # Sorting by thread and variant makes the saved CSVs easier to inspect.
    train = (
        df[df["thread_num"].isin(train_ids)]
        .sort_values(["thread_num", "variant"])
        .drop(columns=["thread_num", "variant"])
        .reset_index(drop=True)
    )
    dev = (
        df[df["thread_num"].isin(dev_ids)]
        .sort_values(["thread_num", "variant"])
        .drop(columns=["thread_num", "variant"])
        .reset_index(drop=True)
    )
    test = (
        df[df["thread_num"].isin(test_ids)]
        .sort_values(["thread_num", "variant"])
        .drop(columns=["thread_num", "variant"])
        .reset_index(drop=True)
    )

    train.to_csv(DATA_DIR / "train.csv", index=False)
    dev.to_csv(DATA_DIR / "dev.csv", index=False)
    test.to_csv(DATA_DIR / "test.csv", index=False)

    print("Saved train/dev/test splits to 581_Sprint_1/data/.")
    print_split_summary("train", train.assign(thread_num=train["arg_id"].str.extract(r"(\d+)").astype(int)))
    print_split_summary("dev", dev.assign(thread_num=dev["arg_id"].str.extract(r"(\d+)").astype(int)))
    print_split_summary("test", test.assign(thread_num=test["arg_id"].str.extract(r"(\d+)").astype(int)))


if __name__ == "__main__":
    main()
