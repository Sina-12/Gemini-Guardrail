import argparse
import json
import os
import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ---------- DRIVER SETUP ----------

def create_driver(timeout=30):
    """
    Create a Chrome driver that looks like a real user.
    Headless is turned off because Reddit blocks it more often.
    """

    chrome_options = Options()

    # chrome_options.add_argument("--headless")  # kept off for reliability

    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # pretend to be a normal browser
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(timeout)
    return driver


# ---------- URL COLLECTION ----------

def collect_post_urls(driver, subreddit, max_posts=100):
    """
    Open the subreddit and scroll until we collect enough unique post URLs.
    """

    url = f"https://www.reddit.com/r/{subreddit}/"
    driver.get(url)

    wait = WebDriverWait(driver, 15)
    collected = set()  # set avoids duplicates

    for _ in range(50):  # scroll multiple times
        try:
            # wait until posts appear on the page
            wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "shreddit-post")))
        except:
            pass

        posts = driver.find_elements(By.TAG_NAME, "shreddit-post")

        for post in posts:
            permalink = post.get_attribute("permalink")

            if permalink:
                full_url = permalink if permalink.startswith("http") else f"https://www.reddit.com{permalink}"
                collected.add(full_url)

            # stop once we have enough
            if len(collected) >= max_posts:
                return list(collected)

        # scroll to load more posts
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    return list(collected)


# ---------- TEXT CLEANUP ----------

def sanitize_filename(title, max_length=100):
    """
    Turn the post title into a safe filename.
    Remove special characters and limit the length.
    """
    sanitized = re.sub(r'[^a-zA-Z0-9]', '_', title)
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    return sanitized[:max_length]


# ---------- EXTRACTION ----------

def extract_post_data(driver):
    """
    Extract structured data:
    - OP author, title, body
    - all comments with author + text
    """

    post_data = {"op": {}, "comments": []}

    posts = driver.find_elements(By.TAG_NAME, "shreddit-post")

    if posts:
        p = posts[0]

        op_author = p.get_attribute("author") or "unknown"
        title = p.get_attribute("post-title") or ""

        try:
            body = p.find_element(By.CSS_SELECTOR, '[slot="text-body"]').text
        except:
            body = ""

        post_data["op"] = {
            "author": f"[OP] u/{op_author}",
            "title": title,
            "body": body
        }

    # collect all comments on the page
    comment_elements = driver.find_elements(By.TAG_NAME, "shreddit-comment")

    for c in comment_elements:
        author = c.get_attribute("author") or "[deleted]"

        try:
            text = c.find_element(By.CSS_SELECTOR, '[slot="comment"]').text
        except:
            text = ""

        post_data["comments"].append({
            "author": f"u/{author}",
            "text": text
        })

    return post_data


# ---------- FILE HELPERS ----------

def load_scraped_urls(log_path):
    """
    Load URLs we already scraped so we do not redo work.
    This lets the script stop and restart safely.
    """
    if not os.path.exists(log_path):
        return set()

    with open(log_path, "r") as f:
        return set(line.strip() for line in f)


def append_scraped_urls(log_path, urls):
    """Save newly scraped URLs to the log file."""
    with open(log_path, "a") as f:
        for url in urls:
            f.write(url + "\n")


# ---------- SAVE ----------

def save_pages(driver, urls, output_dir, json_path, start_index):
    """
    Visit each post and save:
    1. full page text as .txt
    2. structured data in one JSON file
    """

    os.makedirs(output_dir, exist_ok=True)

    # load existing JSON if it exists
    if os.path.exists(json_path):
        with open(json_path) as f:
            json_data = json.load(f)
    else:
        json_data = {}

    for i, url in enumerate(urls):

        driver.get(url)
        time.sleep(2)

        title = driver.title
        safe_title = sanitize_filename(title)

        filename = f"{start_index + i:03d}_{safe_title}.txt"
        filepath = os.path.join(output_dir, filename)

        # save raw page text
        text = driver.execute_script("return document.body.innerText")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)

        # extract structured version
        structured = extract_post_data(driver)

        json_data[url] = {
            "title": title,
            "filename": filename,
            "op": structured["op"],
            "comments": structured["comments"]
        }

        print(f"[{i+1}/{len(urls)}] Saved: {filename}")

    # write updated JSON to disk
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)


# ---------- MAIN ----------

def main():
    """
    Command line usage example:
    python scraper.py changemyview --max-posts 125
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("subreddit")
    parser.add_argument("--max-posts", type=int, default=125)
    args = parser.parse_args()

    # output locations
    output_dir = os.path.join("data", "raw", args.subreddit)
    json_dir = os.path.join("data", "raw", args.subreddit, "json")
    json_path = os.path.join(json_dir, f"{args.subreddit}.json")
    log_path = os.path.join(output_dir, ".scraped_urls.log")

    os.makedirs(json_dir, exist_ok=True)

    driver = create_driver()

    try:
        scraped = load_scraped_urls(log_path)

        print("Collecting post URLs...")
        urls = collect_post_urls(driver, args.subreddit, args.max_posts)

        # only process new URLs
        new_urls = [u for u in urls if u not in scraped]

        if new_urls:
            save_pages(driver, new_urls, output_dir, json_path, len(scraped) + 1)
            append_scraped_urls(log_path, new_urls)
        else:
            print("No new posts to save.")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()