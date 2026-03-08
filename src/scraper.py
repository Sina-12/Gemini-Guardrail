"""
Reddit Subreddit Scraper
========================

This script collects Reddit posts from a subreddit and builds a small corpus
of discussion branches. It first gets post URLs from Reddit's JSON endpoint,
then opens each post on old.reddit.com so the thread structure is easier to
parse.

For each post, the script tries to extract:
1. a successful branch, where the OP appears to have changed their view
2. an unsuccessful branch, where the OP replies but does not award a delta

The final output is saved as a CSV file that can be used for later analysis.

Usage:
    python scraper.py changemyview --target-trees 100 --batch-size 150

Output:
    src/output/{subreddit}/corpus.csv
    src/output/{subreddit}/scraped_urls.txt
"""

import argparse
import csv
import os
import time
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


MIN_BRANCH_DEPTH = 5  # keep only branches with enough back and forth to be useful


def create_driver(timeout=30):
    """Set up Chrome WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1600,2400")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(timeout)
    return driver


def collect_post_urls(subreddit, max_posts=100):
    """
    Collect post URLs from a subreddit using Reddit's JSON feed.

    This avoids scraping the normal subreddit page directly, which is usually
    less reliable. The function keeps fetching pages until it reaches the
    requested number of posts or runs out of results.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; corpus-project/1.0)"
    }

    collected_urls = []
    seen = set()  # helps avoid duplicate URLs
    after = None  # used for Reddit pagination

    while len(collected_urls) < max_posts:
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=100"
        if after:
            url += f"&after={after}"

        print(f"Fetching: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Failed to fetch subreddit JSON: {e}")
            break

        posts = data.get("data", {}).get("children", [])
        if not posts:
            print("No posts returned from Reddit JSON.")
            break

        prev_count = len(collected_urls)

        for post in posts:
            post_data = post.get("data", {})
            permalink = post_data.get("permalink")
            if not permalink:
                continue

            full_url = f"https://www.reddit.com{permalink}".rstrip("/")
            # keep only actual thread links and skip duplicates
            if "/comments/" in full_url and full_url not in seen:
                seen.add(full_url)
                collected_urls.append(full_url)

                if len(collected_urls) >= max_posts:
                    break

        print(f"Collected so far: {len(collected_urls)}")

        # move to the next page of subreddit results
        after = data.get("data", {}).get("after")
        if not after:
            print("No more pages available.")
            break

        # stop if the new page did not add anything
        if len(collected_urls) == prev_count:
            print("No new posts found.")
            break

        time.sleep(1)  # small pause so requests are not too aggressive

    return collected_urls[:max_posts]


def load_scraped_urls(log_path):
    """
    Read the log file of already scraped URLs.

    This helps the scraper avoid reprocessing the same Reddit posts when it is
    run multiple times.
    """
    if not os.path.exists(log_path):
        return set()
    with open(log_path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def append_scraped_urls(log_path, urls):
    """
    Add newly scraped URLs to the log file.

    This keeps track of which posts have already been processed so future runs
    can continue from where the scraper left off.
    """
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")


def _build_comment_tree(driver):
    """
    Build a comment tree from an old.reddit.com thread page.

    This function collects the OP username, the original post text, and all
    comments in the thread. It also stores parent child relationships between
    comments so later functions can trace back and forth discussion branches.
    """
    op_els = driver.find_elements(By.CSS_SELECTOR, ".top-matter .author")
    op_username = op_els[0].text if op_els else "unknown"

    title_els = driver.find_elements(By.CSS_SELECTOR, "a.title")
    post_title = title_els[0].text if title_els else ""

    body_els = driver.find_elements(By.CSS_SELECTOR, ".expando .md")
    body_text = body_els[0].text if body_els else ""

    # combine title and body so the original post becomes depth 0 in the output
    op_text = f"{post_title} {body_text}".strip()

    comment_elements = driver.find_elements(By.CSS_SELECTOR, ".commentarea .comment")
    comments_by_id = {}

    for c in comment_elements:
        thing_id = c.get_attribute("data-fullname") or ""
        if not thing_id:
            continue

        author_els = c.find_elements(By.CSS_SELECTOR, ":scope > .entry .author")
        author = author_els[0].text if author_els else "[deleted]"

        body_els = c.find_elements(By.CSS_SELECTOR, ":scope > .entry .md")
        text = body_els[0].text if body_els else ""

        try:
            # find the closest parent comment above the current one
            parent_el = c.find_element(
                By.XPATH, './ancestor::div[contains(@class, "comment")][1]'
            )
            parent_id = parent_el.get_attribute("data-fullname") or ""
        except Exception:
            parent_id = ""

        # store each comment and leave space to add child comments later
        comments_by_id[thing_id] = {
            "author": author,
            "text": text,
            "thing_id": thing_id,
            "parent_id": parent_id,
            "children": [],
        }

    top_level_ids = []
    for thing_id, node in comments_by_id.items():
        parent_id = node["parent_id"]
        # comments without a valid parent are treated as top level
        if not parent_id or parent_id not in comments_by_id:
            top_level_ids.append(thing_id)
        else:
            comments_by_id[parent_id]["children"].append(thing_id)

    return op_username, op_text, comments_by_id, top_level_ids


def _trace_op_r1_chain(comments_by_id, op_comment_id, r1_username, op_username):
    """
    Follow one conversation chain between the OP and one responder.

    Starting from an OP reply, this function traces upward to recover the
    earlier part of the exchange, then continues downward to extend the chain
    as long as the OP and the same responder keep alternating.
    """
    upward = []
    current_id = op_comment_id

    # first walk upward to recover the earlier part of the chain
    while current_id:
        node = comments_by_id.get(current_id)
        if not node:
            break

        upward.append((node["author"], node["text"], current_id))
        parent_id = node["parent_id"]
        parent = comments_by_id.get(parent_id)

        if not parent:
            break

        # stop if the chain no longer stays between OP and the same responder
        if parent["author"] not in (op_username, r1_username):
            break

        current_id = parent_id

    upward.reverse()

    # remove leading OP comments so the branch starts with the responder
    while upward and upward[0][0] == op_username:
        upward.pop(0)

    if not upward:
        return []

    last_id = upward[-1][2]
    node = comments_by_id.get(last_id)
    expect_op = (node["author"] == r1_username)

    downward = []
    current = node

    # then walk downward as long as the speakers keep alternating
    while current["children"]:
        target = op_username if expect_op else r1_username
        next_id = None

        for child_id in current["children"]:
            child = comments_by_id.get(child_id)
            if child and child["author"] == target:
                next_id = child_id
                break

        if next_id is None:
            break

        current = comments_by_id[next_id]
        downward.append((current["author"], current["text"], next_id))
        expect_op = not expect_op

    full = upward + downward
    return [(author, text) for author, text, _ in full]


def _has_delta(chain, op_username):
    """
    Check whether the OP awarded a delta anywhere in the conversation chain.

    A delta is used here as a sign that the branch was successful in changing
    the OP's view.
    """
    for author, text in chain:
        if author == op_username:
            # check for a few common ways a delta might appear in the text
            if "\u0394" in text or "\u2206" in text or "!delta" in text or "delta" in text.lower():
                return True
    return False


def _chain_to_rows(chain, op_text, op_username, branch_id, success):
    """
    Convert one extracted discussion branch into rows for the output CSV.

    The original post is added first at depth 0, and each later comment in the
    branch is added with its speaker label and depth value.
    """
    rows = [
        {
            "id": branch_id,
            "success": success,
            "speaker_id": f"{branch_id}_OP",
            "text": op_text,
            "depth": 0,
        }
    ]

    for i, (author, text) in enumerate(chain):
        is_op = (author == op_username)
        speaker_tag = "OP" if is_op else "r1"
        rows.append(
            {
                "id": branch_id,
                "success": success,
                "speaker_id": f"{branch_id}_{speaker_tag}",
                "text": text,
                "depth": i + 1,  # depth increases as the conversation continues
            }
        )

    return rows


def extract_branches(driver, post_index):
    """
    Extract the best successful and unsuccessful branches from one Reddit post.

    The function looks for OP reply chains, separates them into delta and
    non-delta branches, ranks them by length, and returns the strongest branch
    from each group if it is long enough.
    """
    op_username, op_text, comments_by_id, top_level_ids = _build_comment_tree(driver)

    seen_chains = set()
    candidate_chains = []

    for tid, node in comments_by_id.items():
        # only start from comments written by the OP
        if node["author"] != op_username:
            continue

        parent = comments_by_id.get(node["parent_id"])
        # skip if there is no parent or if the OP is replying to themselves
        if not parent or parent["author"] == op_username:
            continue

        r1_username = parent["author"]
        if r1_username == "[deleted]":
            continue

        # keep just one chain per responder to avoid duplicates
        if r1_username in seen_chains:
            continue

        seen_chains.add(r1_username)

        chain = _trace_op_r1_chain(comments_by_id, tid, r1_username, op_username)
        if chain:
            candidate_chains.append(chain)

    # split chains into successful and unsuccessful using delta presence
    delta_chains = [c for c in candidate_chains if _has_delta(c, op_username)]
    no_delta_chains = [c for c in candidate_chains if not _has_delta(c, op_username)]

    # longer branches are usually more informative, so rank by length
    delta_chains.sort(key=len, reverse=True)
    no_delta_chains.sort(key=len, reverse=True)

    s_rows = []
    u_rows = []

    if delta_chains:
        best = delta_chains[0]
        if len(best) + 1 >= MIN_BRANCH_DEPTH:
            s_rows = _chain_to_rows(best, op_text, op_username, f"s{post_index}_s", 1)

    if no_delta_chains:
        best = no_delta_chains[0]
        if len(best) + 1 >= MIN_BRANCH_DEPTH:
            u_rows = _chain_to_rows(best, op_text, op_username, f"s{post_index}_u", 0)

    return s_rows, u_rows


def process_posts(driver, urls, output_dir, csv_path, start_index=0):
    """
    Visit each Reddit post URL, extract usable branches, and save them to CSV.

    This is the main processing step of the scraper. It opens each post,
    tries to find successful and unsuccessful branches, and writes all valid
    rows to the output file.
    """
    os.makedirs(output_dir, exist_ok=True)

    all_rows = []
    trees_found = 0

    for i, url in enumerate(urls):
        post_index = start_index + i
        try:
            old_url = url.replace("www.reddit.com", "old.reddit.com")
            if "?" not in old_url:
                old_url += "?limit=500"
            else:
                old_url += "&limit=500"

            driver.get(old_url)
            time.sleep(3)  # give the thread page time to load fully

            s_rows, u_rows = extract_branches(driver, post_index)
            all_rows.extend(s_rows)
            all_rows.extend(u_rows)

            # count the post if it produced at least one usable branch
            if s_rows or u_rows:
                trees_found += 1

            s_tag = f"{len(s_rows)}rows" if s_rows else "skip"
            u_tag = f"{len(u_rows)}rows" if u_rows else "skip"
            print(f"[{i + 1}/{len(urls)}] s={s_tag} u={u_tag} | {url}")

        except Exception as e:
            print(f"[{i + 1}/{len(urls)}] Failed: {url}: {e}")
            continue

    if not all_rows:
        print("No qualifying branches found.")
        return trees_found

    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "success", "speaker_id", "text", "depth"],
        )
        if write_header:
            writer.writeheader()
        writer.writerows(all_rows)

    print(f"CSV saved to {csv_path} ({len(all_rows)} rows written)")
    return trees_found


def main():
    """
    Run the scraper from the command line.

    This function reads the user arguments, sets up file paths, collects new
    post URLs, processes them, and keeps going until the target number of
    qualifying trees has been reached or no new posts are available.
    """
    parser = argparse.ArgumentParser(
        description="Scrape subreddit conversation branches into CSV."
    )
    parser.add_argument(
        "subreddit",
        help="Name of the subreddit to scrape (e.g., 'changemyview')",
    )
    parser.add_argument(
        "--target-trees",
        type=int,
        default=100,
        help="Number of posts with qualifying branches to collect (default: 100)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=300,
        help="Number of URLs to collect per batch (default: 100)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Page load timeout in seconds (default: 30)",
    )
    args = parser.parse_args()

    output_dir = os.path.join("output", args.subreddit)
    csv_path = os.path.join(output_dir, "corpus.csv")
    log_path = os.path.join(output_dir, "scraped_urls.txt")

    print(f"Starting scraper for r/{args.subreddit} (target: {args.target_trees} trees)")

    driver = create_driver(timeout=args.timeout)
    total_trees = 0

    try:
        while total_trees < args.target_trees:
            previously_scraped = load_scraped_urls(log_path)
            if previously_scraped:
                print(f"Already scraped {len(previously_scraped)} URLs.")

            print(f"\nCollecting up to {args.batch_size} post URLs...")
            urls = collect_post_urls(args.subreddit, max_posts=args.batch_size)
            print(f"Collected {len(urls)} post URLs.")

            # remove URLs that were already processed in earlier runs
            new_urls = [u for u in urls if u not in previously_scraped]
            skipped = len(urls) - len(new_urls)
            if skipped:
                print(f"Skipping {skipped} already scraped URLs. {len(new_urls)} new URLs remain.")

            if not new_urls:
                print("No new URLs available.")
                break

            start_index = len(previously_scraped)
            print("Extracting conversation branches...")
            trees_found = process_posts(
                driver,
                new_urls,
                output_dir,
                csv_path,
                start_index=start_index,
            )
            total_trees += trees_found

            append_scraped_urls(log_path, new_urls)
            print(f"Trees so far: {total_trees}/{args.target_trees}")

            if total_trees >= args.target_trees:
                print(f"\nTarget reached! {total_trees} trees collected.")
            else:
                remaining = args.target_trees - total_trees
                print(f"\nNeed {remaining} more trees. Fetching more posts...")
    finally:
        driver.quit()  # always close the browser, even if something fails

    print(f"Done. Output saved to {output_dir}/")


if __name__ == "__main__":
    main()