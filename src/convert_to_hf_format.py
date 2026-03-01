import json
import pandas as pd
from pathlib import Path

# path to the original Hugging Face dataset (our base corpus)
HF_CSV = Path("data/raw/corpus_raw.csv")

# path to the JSON file produced by our Reddit scraper
SCRAPED_JSON = Path("data/raw/changemyview/json/changemyview.json")


def convert_scraped_to_rows(json_path):
    """
    Convert the scraped Reddit JSON into the same format
    as the HF dataset.

    Each row will look like:
    ### Human: <OP text>
    ### Assistant: <reply text>
    """

    # load the scraped JSON file
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    rows = []  # store all usable training instances here

    # loop through each scraped post
    for post in data.values():

        # get OP title and body (empty string if missing)
        title = post["op"].get("title", "")
        body = post["op"].get("body", "")

        # combine them to form the "Human" part
        human = f"{title}\n\n{body}".strip()

        comments = post.get("comments", [])

        # skip posts with no comments
        if not comments:
            continue

        assistant = None

        # take the first non-empty comment as the reply
        for c in comments:
            text = c.get("text", "").strip()
            if text:
                assistant = text
                break

        # skip if we couldn't find a usable reply
        if not assistant:
            continue

        # format to match the HF training schema
        formatted = f"### Human: {human}\n### Assistant: {assistant}"

        rows.append({"train": formatted})  # same column name as HF data

    # return as a dataframe so it can be concatenated easily
    return pd.DataFrame(rows)


def main():

    # load the existing HF corpus
    print("Loading existing HF corpus...")
    hf_df = pd.read_csv(HF_CSV)

    # convert scraped JSON into the same format
    print("Converting scraped data...")
    scraped_df = convert_scraped_to_rows(SCRAPED_JSON)

    print(f"New usable rows: {len(scraped_df)}")

    # append scraped rows to the bottom of the original dataset
    combined = pd.concat([hf_df, scraped_df], ignore_index=True)

    # overwrite the CSV with the expanded corpus
    combined.to_csv(HF_CSV, index=False)

    print(f"Done. Final size: {len(combined)} rows")


# run the script
if __name__ == "__main__":
    main()