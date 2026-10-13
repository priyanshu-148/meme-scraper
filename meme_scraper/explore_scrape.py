"""
Generic page scraper (Playwright). Defaults are set up for old.reddit.com,
which has simple static HTML and pagination, so it works out of the box.
To use another site, change the SELECTORS and the ATTR/TEXT helpers below.

Usage:
    python explore_scrape.py
    python explore_scrape.py --url "https://old.reddit.com/r/dankmemes/top/?t=week" --max 50
    python explore_scrape.py --no-filter      # skip the funny-keyword filter
"""
import argparse
import hashlib
import json
import random
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from playwright.sync_api import sync_playwright

from filters import looks_like_funny, passes_content_filter

# ======== SETTINGS ========
START_URL = "https://old.reddit.com/r/memes/top/?t=week"
MAX_ITEMS = 100
MAX_PAGES = 20
HEADLESS = True
IMG_DIR = Path("images")
META_FILE = Path("metadata.jsonl")
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

# old.reddit selectors
SEL_POST = "div.thing[data-type='link']"
SEL_TITLE = "a.title"
SEL_NEXT = "span.next-button a"
# ==========================

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")


def download(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=15, stream=True, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        if not r.headers.get("content-type", "").startswith("image"):
            return False
        with dest.open("wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"[warn] download failed {url}: {e}")
        return False


def load_seen() -> set[str]:
    seen = set()
    if META_FILE.exists():
        for line in META_FILE.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(json.loads(line)["post_id"])
            except Exception:
                pass
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=START_URL)
    ap.add_argument("--max", type=int, default=MAX_ITEMS)
    ap.add_argument("--no-filter", action="store_true", help="skip funny-keyword filter")
    ap.add_argument("--show", action="store_true", help="show the browser window")
    args = ap.parse_args()

    IMG_DIR.mkdir(exist_ok=True)
    seen = load_seen()
    saved = 0

    with META_FILE.open("a", encoding="utf-8") as meta, sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=HEADLESS and not args.show)  # uses your installed Chrome
        page = browser.new_context(user_agent=USER_AGENT).new_page()
        url = args.url

        for page_num in range(1, MAX_PAGES + 1):
            print(f"Page {page_num}: {url}")
            page.goto(url, wait_until="domcontentloaded")
            try:
                page.wait_for_selector(SEL_POST, timeout=15000)
            except Exception:
                print("No posts found - check SEL_POST or whether the site blocked us.")
                break

            for post in page.query_selector_all(SEL_POST):
                post_id = post.get_attribute("data-fullname")
                if not post_id or post_id in seen:
                    continue
                seen.add(post_id)

                if post.get_attribute("data-nsfw") == "true":
                    continue
                img_url = post.get_attribute("data-url") or ""
                if Path(urlparse(img_url).path).suffix.lower() not in IMAGE_EXTS:
                    continue

                title_el = post.query_selector(SEL_TITLE)
                title = title_el.inner_text().strip() if title_el else ""
                sub = post.get_attribute("data-subreddit")
                if not args.no_filter and not looks_like_funny(title, sub):
                    continue

                suffix = Path(urlparse(img_url).path).suffix
                path = IMG_DIR / (hashlib.sha1(img_url.encode()).hexdigest()[:16] + suffix)
                if not path.exists() and not download(img_url, path):
                    continue
                if not passes_content_filter(path):
                    path.unlink(missing_ok=True)
                    continue

                meta.write(json.dumps({
                    "post_id": post_id,
                    "title": title,
                    "author": post.get_attribute("data-author"),
                    "subreddit": sub,
                    "url": img_url,
                    "image_path": str(path),
                    "source": args.url,
                }) + "\n")
                meta.flush()
                saved += 1
                print(f"[{saved:4d}] {title[:50]}")
                if saved >= args.max:
                    break

            if saved >= args.max:
                break
            nxt = page.query_selector(SEL_NEXT)
            if not nxt:
                print("No next page.")
                break
            url = nxt.get_attribute("href")
            time.sleep(2 + random.uniform(0, 1.5))  # be polite

        browser.close()
    print(f"Done. Saved {saved} images to {IMG_DIR}/")


if __name__ == "__main__":
    main()
