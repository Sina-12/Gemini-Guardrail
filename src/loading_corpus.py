import os
import pandas as pd
from datasets import load_dataset

def main():

    # folder where the raw corpus will be stored
    output_dir = os.path.join("data", "raw")

    # final CSV path for the downloaded dataset
    output_file = os.path.join(output_dir, "corpus_raw.csv")

    # create the folder if it does not exist
    if not os.path.exists(output_dir):
        print(f"Creating directory: {output_dir}")
        os.makedirs(output_dir)

    """
    If the file already exists, we do not download again.
    This allows the script to be rerun safely and
    avoids wasting time and bandwidth.
    """
    if os.path.exists(output_file):
        print(f"Restarting: Found {output_file}. Skipping download.")
        df = pd.read_csv(output_file)  # load existing corpus

    else:
        print("Starting: Downloading dataset from Hugging Face...")

        # load the CMV dataset directly from Hugging Face
        dataset = load_dataset(
            "Siddish/change-my-view-subreddit-cleaned",
            split='train'
        )

        # convert to pandas so we can save it as CSV
        df = dataset.to_pandas()

        # save the raw corpus locally for reproducibility
        df.to_csv(output_file, index=False)

        print(f"Success: Saved {len(df)} instances to {output_file}.")


# run the script from the command line
if __name__ == "__main__":
    main()