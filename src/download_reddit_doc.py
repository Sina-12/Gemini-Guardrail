import json
import requests
from pathlib import Path

# where the downloaded document will be saved
OUT_PATH = Path("data/raw/reddit_comment.json")

# example Reddit thread in JSON format
URL = "https://old.reddit.com/comments/1i12n7.json"

# identify our script so Reddit does not block the request
HEADERS = {
    "User-Agent": "mds-cl-corpus-project/0.1"
}


def main():
    # send a request to get the thread data
    response = requests.get(URL, headers=HEADERS)

    # stop if the request did not work
    if response.status_code != 200:
        print(f"Request failed: {response.status_code}")
        print("Check if the Reddit post exists or if the URL is correct.")
        return

    # convert the response into Python format
    data = response.json()

    # take the first top-level comment as one document
    comment = data[1]["data"]["children"][0]["data"]["body"]

    # make sure the output folder exists
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # save the text in JSON so we can add metadata later
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"text": comment}, f, indent=2, ensure_ascii=False)

    # print a message so we know the script worked
    print("Downloaded one document to", OUT_PATH)


if __name__ == "__main__":
    main()