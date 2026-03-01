import argparse
import json
import os
import re
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


def sanitize_filename(title, max_length=100):
    """Replace non-alphanumeric characters with underscores and truncate."""
    sanitized = re.sub(r'[^a-zA-Z0-9]', '_', title)
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    return sanitized[:max_length]


def get_page_title(driver):
    """Extract page title from the browser."""
    try:
        return driver.title
    except Exception:
        return "untitled"


def extract_post_data(driver):
    """Extract structured post and comment data from a Reddit post page."""
    post_data = {"op": {}, "comments": []}

    # Extract OP info from shreddit-post
    posts = driver.find_elements(By.TAG_NAME, "shreddit-post")
    if posts:
        p = posts[0]
        op_author = p.get_attribute("author") or "unknown"
        post_title = p.get_attribute("post-title") or ""
        try:
            body_el = p.find_element(By.CSS_SELECTOR, 'div[id$="-post-rtjson-content"]')
            body_text = body_el.text
        except Exception:
            try:
                body_el = p.find_element(By.CSS_SELECTOR, '[slot="text-body"]')
                body_text = body_el.text
            except Exception:
                body_text = ""
        post_data["op"] = {
            "author": f"[OP] u/{op_author}",
            "title": post_title,
            "body": body_text,
        }
    else:
        post_data["op"] = {"author": "[OP] u/unknown", "title": "", "body": ""}

    op_username = (posts[0].get_attribute("author") or "") if posts else ""

    # Extract comments from shreddit-comment elements
    comment_elements = driver.find_elements(By.TAG_NAME, "shreddit-comment")
    comments_by_id = {}
    top_level_ids = []

    for c in comment_elements:
        author = c.get_attribute("author") or "[deleted]"
        depth = int(c.get_attribute("depth") or 0)
        thing_id = c.get_attribute("thingid") or ""
        parent_id = c.get_attribute("parentid") or ""

        try:
            content_div = c.find_element(By.CSS_SELECTOR, 'div[id$="-comment-rtjson-content"]')
            text = content_div.text
        except Exception:
            text = ""

        is_op = (author == op_username)
        display_author = f"[OP] u/{author}" if is_op else f"u/{author}"

        comment_node = {
            "author": display_author,
            "depth": depth,
            "text": text,
            "replies": [],
        }

        comments_by_id[thing_id] = comment_node

        if depth == 0:
            top_level_ids.append(thing_id)
        elif parent_id in comments_by_id:
            comments_by_id[parent_id]["replies"].append(comment_node)

    post_data["comments"] = [comments_by_id[tid] for tid in top_level_ids]
    return post_data


def load_json_data(json_path):
    """Load existing JSON data, or return empty dict."""
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json_data(json_path, data):
    """Write JSON data to file."""
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_pages(driver, urls, output_dir, json_path, start_index=1):
    """Visit each URL and save the page text content to a txt file and JSON."""
    os.makedirs(output_dir, exist_ok=True)

    json_data = load_json_data(json_path)

    for i, url in enumerate(urls):
        index = start_index + i
        try:
            driver.get(url)
            time.sleep(2)

            title = get_page_title(driver)
            text_content = driver.execute_script("return document.body.innerText")

            safe_title = sanitize_filename(title)
            filename = f"{index:03d}_{safe_title}.txt"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text_content)

            structured = extract_post_data(driver)
            json_data[url] = {
                "index": index,
                "title": title,
                "filename": filename,
                "op": structured["op"],
                "comments": structured["comments"],
            }

            print(f"[{i + 1}/{len(urls)}] Saved: {filename}")

        except Exception as e:
            print(f"[{i + 1}/{len(urls)}] Failed to save {url}: {e}")
            continue

    save_json_data(json_path, json_data)
    print(f"JSON saved to {json_path} ({len(json_data)} total entries)")


def main():
    parser = argparse.ArgumentParser(description="Scrape the first 100 entries of a subreddit.")
    parser.add_argument("subreddit", help="Name of the subreddit to scrape (e.g., 'python')")
    parser.add_argument("--max-posts", type=int, default=100, help="Maximum number of posts to collect (default: 100)")
    parser.add_argument("--timeout", type=int, default=30, help="Page load timeout in seconds (default: 30)")
    args = parser.parse_args()

    output_dir = os.path.join("output", args.subreddit)
    json_dir = os.path.join("json_output", args.subreddit)
    json_path = os.path.join(json_dir, f"{args.subreddit}.json")
    log_path = os.path.join(output_dir, ".scraped_urls.log")

    print(f"Starting scraper for r/{args.subreddit}")

    previously_scraped = load_scraped_urls(log_path)
    if previously_scraped:
        print(f"Found {len(previously_scraped)} previously scraped URLs, will skip them.")

    driver = create_driver(timeout=args.timeout)

    try:
        print("Collecting post URLs...")
        urls = collect_post_urls(driver, args.subreddit, max_posts=args.max_posts)
        print(f"Collected {len(urls)} post URLs.")

        new_urls = [u for u in urls if u not in previously_scraped]
        skipped = len(urls) - len(new_urls)
        if skipped:
            print(f"Skipping {skipped} already-scraped URLs. {len(new_urls)} new URLs to process.")

        if new_urls:
            # Use a starting index that continues from existing files
            start_index = len(previously_scraped) + 1
            print("Saving page content...")
            save_pages(driver, new_urls, output_dir, json_path, start_index=start_index)
            append_scraped_urls(log_path, new_urls)
            print(f"Done. Output saved to {output_dir}/")
        else:
            print("No new posts to save.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
