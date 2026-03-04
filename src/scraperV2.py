"""
Reddit Subreddit Scraper
========================

How to Use
----------
This script scrapes posts from a given subreddit using Selenium with headless
Chrome. It collects post URLs by scrolling the subreddit listing page, then
visits each post to extract its text content and structured comment data.

Prerequisites:
    - Python 3.8+
    - Google Chrome installed
    - ChromeDriver compatible with your Chrome version
    - Install dependencies: pip install -r requirements.txt

Usage:
    python scraper.py <subreddit_name> [--max-posts N] [--timeout N]

Examples:
    python scraper.py python                  # Scrape 100 posts from r/python
    python scraper.py changemyview --max-posts 50   # Scrape 50 posts from r/changemyview
    python scraper.py learnpython --timeout 60      # Use a 60s page load timeout

Output:
    - CSV corpus:  output/<subreddit>/corpus.csv
    - URL list:    output/<subreddit>/scraped_urls.txt

For each post, the scraper extracts two conversation branches:
    - Successful (_s): a thread where OP awarded a delta (view changed)
    - Unsuccessful (_u): a thread where OP engaged but did NOT change view

Each branch follows a single OP <-> r1 back-and-forth to its conclusion.
Only branches with at least 5 turns (OP post + 4 comments) are included.
The scraper tracks previously scraped URLs in a log file so that re-running
the script on the same subreddit will only fetch new posts.
"""

import argparse
import csv
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def create_driver(timeout=30):
    """Set up headless Chrome WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(timeout)
    return driver


def collect_post_urls(driver, subreddit, max_posts=100):
    """Navigate to subreddit and scroll until max_posts unique URLs are collected."""
    url = f"https://www.reddit.com/r/{subreddit}/"
    driver.get(url)
    time.sleep(3)

    collected_urls = []
    seen = set()
    max_scroll_attempts = 50
    no_new_count = 0

    for _ in range(max_scroll_attempts):
        # Reddit uses <shreddit-post> web components with a permalink attribute
        posts = driver.find_elements(By.TAG_NAME, "shreddit-post")
        for post in posts:
            permalink = post.get_attribute("permalink")
            if permalink:
                href = permalink if permalink.startswith("http") else f"https://www.reddit.com{permalink}"
                if href not in seen:
                    seen.add(href)
                    collected_urls.append(href)
                    if len(collected_urls) >= max_posts:
                        break

        if len(collected_urls) >= max_posts:
            break

        prev_count = len(collected_urls)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        if len(collected_urls) == prev_count:
            no_new_count += 1
            if no_new_count >= 5:
                print(f"No new posts found after scrolling. Collected {len(collected_urls)} posts.")
                break
        else:
            no_new_count = 0

    return collected_urls


def load_scraped_urls(log_path):
    """Load previously scraped URLs from the log file."""
    if not os.path.exists(log_path):
        return set()
    with open(log_path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def append_scraped_urls(log_path, urls):
    """Append newly scraped URLs to the log file."""
    with open(log_path, "a", encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")



MIN_BRANCH_DEPTH = 5  # OP post (depth 0) + at least 4 comments (depths 1-4)


def _build_comment_tree(driver):
    """Parse old.reddit.com comment elements into a comment tree and return OP info.

    Uses old.reddit.com which renders the full comment tree (new Reddit only
    loads top-level comments). Parent-child relationships are determined via
    DOM nesting (ancestor .comment elements).

    Returns:
        (op_username, op_text, comments_by_id, top_level_ids)
        - op_username: OP's Reddit username string
        - op_text: Combined title + body of OP's post
        - comments_by_id: dict mapping data-fullname -> comment node
        - top_level_ids: list of fullnames for top-level comments
    """
    # Extract OP info from old Reddit layout
    op_els = driver.find_elements(By.CSS_SELECTOR, ".top-matter .author")
    op_username = op_els[0].text if op_els else "unknown"

    title_els = driver.find_elements(By.CSS_SELECTOR, "a.title")
    post_title = title_els[0].text if title_els else ""

    body_els = driver.find_elements(By.CSS_SELECTOR, ".expando .md")
    body_text = body_els[0].text if body_els else ""

    op_text = f"{post_title} {body_text}".strip()

    # Parse all comments
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

        # Get parent comment ID via closest ancestor .comment element
        try:
            parent_el = c.find_element(
                By.XPATH, './ancestor::div[contains(@class, "comment")][1]'
            )
            parent_id = parent_el.get_attribute("data-fullname") or ""
        except Exception:
            parent_id = ""

        comments_by_id[thing_id] = {
            "author": author,
            "text": text,
            "thing_id": thing_id,
            "parent_id": parent_id,
            "children": [],
        }

    # Link children to parents
    top_level_ids = []
    for thing_id, node in comments_by_id.items():
        parent_id = node["parent_id"]
        if not parent_id or parent_id not in comments_by_id:
            top_level_ids.append(thing_id)
        else:
            comments_by_id[parent_id]["children"].append(thing_id)

    return op_username, op_text, comments_by_id, top_level_ids


def _trace_op_r1_chain(comments_by_id, op_comment_id, r1_username, op_username):
    """Trace a full OP <-> r1 chain given an OP comment and r1's username.

    Walks UP from the OP comment to find where the OP-r1 exchange started,
    then walks DOWN to find where it ends. Only includes turns between
    these two specific users.

    Returns:
        list of (author, text) tuples in conversation order (excluding the
        OP's original post which is added separately as depth 0).
    """
    # Walk UP to find the start of the OP <-> r1 exchange
    # From the OP comment, the parent should be r1, grandparent should be OP, etc.
    upward = []
    current_id = op_comment_id
    while current_id:
        node = comments_by_id.get(current_id)
        if not node:
            break
        upward.append((node["author"], node["text"], current_id))
        parent_id = node["parent_id"]
        parent = comments_by_id.get(parent_id)
        if not parent:
            break
        # Only continue up if parent is one of our two speakers
        if parent["author"] not in (op_username, r1_username):
            break
        current_id = parent_id

    # Reverse so chain goes from earliest to latest
    upward.reverse()

    # The chain should start with r1's comment, so trim any leading OP turns
    while upward and upward[0][0] == op_username:
        upward.pop(0)

    if not upward:
        return []

    # Walk DOWN from the last comment in the upward chain
    last_id = upward[-1][2]
    node = comments_by_id.get(last_id)
    # Determine who we expect next
    expect_op = (node["author"] == r1_username)

    downward = []
    current = node
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

    # Combine: upward chain + downward continuation
    full = upward + downward
    return [(author, text) for author, text, _ in full]


def _has_delta(chain, op_username):
    """Check if any OP turn in the chain contains a delta award."""
    for author, text in chain:
        if author == op_username:
            if "\u0394" in text or "\u2206" in text or "!delta" in text:
                return True
    return False


def _chain_to_rows(chain, op_text, op_username, branch_id, success):
    """Convert a conversation chain to CSV row dicts.

    Prepends the OP's original post as depth 0, then each chain turn
    gets incrementing depth.
    """
    rows = []
    # Depth 0: OP's original post
    rows.append({
        "id": branch_id,
        "success": success,
        "speaker_id": f"{branch_id}_OP",
        "text": op_text,
        "depth": 0,
    })
    for i, (author, text) in enumerate(chain):
        is_op = (author == op_username)
        speaker_tag = "OP" if is_op else "r1"
        rows.append({
            "id": branch_id,
            "success": success,
            "speaker_id": f"{branch_id}_{speaker_tag}",
            "text": text,
            "depth": i + 1,
        })
    return rows


def extract_branches(driver, post_index):
    """Extract successful and unsuccessful conversation branches from a post.

    Finds OP <-> r1 exchanges anywhere in the comment tree (not just from
    top-level comments). For each OP comment, identifies the conversation
    partner (r1) and traces the full chain up and down.

    Returns:
        (s_rows, u_rows) — each is a list of row dicts, or empty list if
        no qualifying branch was found. Unsuccessful branches must have
        >= MIN_BRANCH_DEPTH rows; successful branches have no minimum.
    """
    op_username, op_text, comments_by_id, top_level_ids = _build_comment_tree(driver)

    # Find all OP comments and trace their conversation chains
    seen_chains = set()  # deduplicate by r1 username
    candidate_chains = []

    for tid, node in comments_by_id.items():
        if node["author"] != op_username:
            continue
        # The parent of this OP comment is r1
        parent = comments_by_id.get(node["parent_id"])
        if not parent or parent["author"] == op_username:
            continue
        r1_username = parent["author"]
        if r1_username == "[deleted]":
            continue

        # Deduplicate: one chain per unique r1 user
        if r1_username in seen_chains:
            continue
        seen_chains.add(r1_username)

        chain = _trace_op_r1_chain(comments_by_id, tid, r1_username, op_username)
        if chain:
            candidate_chains.append(chain)

    # Separate into delta (successful) and non-delta (unsuccessful) chains
    delta_chains = [c for c in candidate_chains if _has_delta(c, op_username)]
    no_delta_chains = [c for c in candidate_chains if not _has_delta(c, op_username)]

    # Pick the longest chain from each group
    delta_chains.sort(key=len, reverse=True)
    no_delta_chains.sort(key=len, reverse=True)

    s_rows = []
    u_rows = []

    # Successful branch (no minimum depth — any delta exchange counts)
    if delta_chains:
        best = delta_chains[0]
        s_rows = _chain_to_rows(best, op_text, op_username, f"s{post_index}_s", 1)

    # Unsuccessful branch (must meet minimum depth)
    if no_delta_chains:
        best = no_delta_chains[0]
        rows = _chain_to_rows(best, op_text, op_username, f"s{post_index}_u", 0)
        if len(rows) >= MIN_BRANCH_DEPTH:
            u_rows = rows

    return s_rows, u_rows


def process_posts(driver, urls, output_dir, csv_path, start_index=0):
    """Visit each URL, extract conversation branches, and write to CSV."""
    os.makedirs(output_dir, exist_ok=True)

    all_rows = []
    trees_found = 0
    for i, url in enumerate(urls):
        post_index = start_index + i
        try:
            # Use old.reddit.com to get the full comment tree
            old_url = url.replace("www.reddit.com", "old.reddit.com")
            if "?" not in old_url:
                old_url += "?limit=500"
            else:
                old_url += "&limit=500"
            driver.get(old_url)
            time.sleep(3)

            s_rows, u_rows = extract_branches(driver, post_index)
            all_rows.extend(s_rows)
            all_rows.extend(u_rows)

            has_branch = bool(s_rows or u_rows)
            if has_branch:
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

    # Append to existing CSV or create with headers
    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "success", "speaker_id", "text", "depth"])
        if write_header:
            writer.writeheader()
        writer.writerows(all_rows)

    print(f"CSV saved to {csv_path} ({len(all_rows)} rows written)")
    return trees_found


def main():
    # --- Step 1: Parse command-line arguments ---
    parser = argparse.ArgumentParser(description="Scrape subreddit conversation branches into CSV.")
    parser.add_argument("subreddit", help="Name of the subreddit to scrape (e.g., 'changemyview')")
    parser.add_argument("--target-trees", type=int, default=100,
                        help="Number of posts with qualifying branches to collect (default: 100)")
    parser.add_argument("--batch-size", type=int, default=100,
                        help="Number of URLs to collect per batch (default: 100)")
    parser.add_argument("--timeout", type=int, default=30,
                        help="Page load timeout in seconds (default: 30)")
    args = parser.parse_args()

    # --- Step 2: Define output paths ---
    output_dir = os.path.join("output", args.subreddit)
    csv_path = os.path.join(output_dir, "corpus.csv")
    log_path = os.path.join(output_dir, "scraped_urls.txt")

    print(f"Starting scraper for r/{args.subreddit} (target: {args.target_trees} trees)")

    # --- Step 3: Initialize browser ---
    driver = create_driver(timeout=args.timeout)
    total_trees = 0

    try:
        while total_trees < args.target_trees:
            # --- Step 4: Load previously scraped URLs ---
            previously_scraped = load_scraped_urls(log_path)
            if previously_scraped:
                print(f"Already scraped {len(previously_scraped)} URLs.")

            # --- Step 5: Collect a batch of post URLs ---
            print(f"\nCollecting up to {args.batch_size} post URLs...")
            urls = collect_post_urls(driver, args.subreddit, max_posts=args.batch_size)
            print(f"Collected {len(urls)} post URLs.")

            # --- Step 6: Filter out already-scraped URLs ---
            new_urls = [u for u in urls if u not in previously_scraped]
            skipped = len(urls) - len(new_urls)
            if skipped:
                print(f"Skipping {skipped} already-scraped. {len(new_urls)} new URLs.")

            if not new_urls:
                print("No new URLs available. The subreddit may not have enough posts.")
                break

            # --- Step 7: Process new URLs and extract branches ---
            start_index = len(previously_scraped)
            print("Extracting conversation branches...")
            trees_found = process_posts(driver, new_urls, output_dir, csv_path,
                                        start_index=start_index)
            total_trees += trees_found

            # --- Step 8: Log scraped URLs ---
            append_scraped_urls(log_path, new_urls)
            print(f"Trees so far: {total_trees}/{args.target_trees}")

            if total_trees >= args.target_trees:
                print(f"\nTarget reached! {total_trees} trees collected.")
            else:
                remaining = args.target_trees - total_trees
                print(f"\nNeed {remaining} more trees. Scrolling for more posts...")
    finally:
        driver.quit()

    print(f"Done. Output saved to {output_dir}/")


if __name__ == "__main__":
    main()
