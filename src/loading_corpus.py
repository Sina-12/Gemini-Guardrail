import os
import pandas as pd
from datasets import load_dataset

def main():
    output_dir = "data"
    output_file = os.path.join(output_dir, "corpus_raw.csv")

    if not os.path.exists(output_dir):
        print(f"Creating directory: {output_dir}")
        os.makedirs(output_dir)

    if os.path.exists(output_file):
        print(f"Restarting: Found {output_file}. Skipping download.")
        df = pd.read_csv(output_file)
    else:
        print("Starting: Downloading dataset from Hugging Face...")
        dataset = load_dataset("Siddish/change-my-view-subreddit-cleaned", split='train')
        df = dataset.to_pandas()
        df.to_csv(output_file, index = False)
        print(f"Success: Saved {len(df)} instances to {output_file}.")

if __name__ == "__main__":
    main()

