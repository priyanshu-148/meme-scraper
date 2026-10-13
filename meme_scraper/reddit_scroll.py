"""
Opens Chrome, scrolls a Reddit page like a person would, and saves LINKS (not images)
to links.csv for posts that pass your filters. Open links.csv in Excel/Sheets.

Just click Run in VS Code. A Chrome window will open and scroll by itself.
Tip: don't log in with your main account.
"""
from __future__ import annotations
import csv
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from filters import looks_like_funny

# ======== SETTINGS ========
URLS = [
    "https://www.reddit.com/r/memes/top/?t=week",
    "https://www.reddit.com/r/dankmemes/top/?t=week",
    "https://www.reddit.com/r/funny/top/?t=week",
]
MAX_SAVED_PER_URL = 50
MAX_SCROLLS_PER_URL = 40
MIN_SCORE = 1000          # minimum upvotes (net score)
MIN_Q = 20                # "quality" = upvotes per hour since posting
MIN_COMMENT_RATIO = 0.01  # comments / score, filters out pure vote-farm posts
IMAGES_ONLY = True
OUT_FILE = Path("links.csv")
DEBUG = False             # True prints the raw attributes of the first post (for fixing selectors)
# ==========================

FIELDS = ["permalink", "title", "subreddit", "score", "comments", "q_per_hour", "content_url"]


def age_hours(ts: str | None) -> float:
    try:
        ts = ts.replace("Z", "+00:00").replace("+0000", "+00:00")
        dt = datetime.fromisoformat(ts)
        return max((datetime.now(timezone.utc) - dt).total_seconds() / 3600, 1.0)
    except Exception:
        return 24.0


def load_seen() -> set[str]:
    if not OUT_FILE.exists():
        return set()
    with OUT_FILE.open(encoding="utf-8", newline="") as f:
        return {row["permalink"] for row in csv.DictReader(f)}


def main():
    seen = load_seen()
    new_file = not OUT_FILE.exists()
    total = 0

    with OUT_FILE.open("a", encoding="utf-8", newline="") as f, sync_playwright() as p:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()

        browser = p.chromium.launch(channel="chrome", headless=False)
        page = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()

        for url in URLS:
            print(f"\n== {url}")
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(4)
            saved, stale = 0, 0
            debug_done = False

            for _ in range(MAX_SCROLLS_PER_URL):
                posts = page.query_selector_all("shreddit-post")
                if DEBUG and posts and not debug_done:
                    print(posts[0].evaluate(
                        "el => Object.fromEntries([...el.attributes].map(a => [a.name, a.value]))"))
                    debug_done = True

                new_posts = 0
                for post in posts:
                    link = post.get_attribute("permalink")
                    if not link or link in seen:
                        continue
                    seen.add(link)
                    new_posts += 1

                    if IMAGES_ONLY and post.get_attribute("post-type") != "image":
                        continue
                    try:
                        score = int(post.get_attribute("score") or 0)
                        comments = int(post.get_attribute("comment-count") or 0)
                    except ValueError:
                        continue

                    q = score / age_hours(post.get_attribute("created-timestamp"))
                    title = post.get_attribute("post-title") or ""
                    sub = (post.get_attribute("subreddit-prefixed-name") or "").replace("r/", "")

                    if score < MIN_SCORE or q < MIN_Q:
                        continue
                    if comments / max(score, 1) < MIN_COMMENT_RATIO:
                        continue
                    if not looks_like_funny(title, sub):
                        continue

                    writer.writerow({
                        "permalink": "https://www.reddit.com" + link,
                        "title": title, "subreddit": sub, "score": score,
                        "comments": comments, "q_per_hour": round(q, 1),
                        "content_url": post.get_attribute("content-href") or "",
                    })
                    f.flush()
                    saved += 1
                    total += 1
                    print(f"[{saved:3d}] {score:>6} pts | {q:6.1f}/hr | {title[:50]}")
                    if saved >= MAX_SAVED_PER_URL:
                        break

                if saved >= MAX_SAVED_PER_URL:
                    break
                stale = stale + 1 if new_posts == 0 else 0
                if stale >= 4:
                    print("No more new posts loading.")
                    break

                # scroll a bit like a person: uneven distance, uneven pauses
                page.evaluate(f"window.scrollBy(0, {random.randint(700, 1400)})")
                time.sleep(random.uniform(1.5, 4.0))

            time.sleep(random.uniform(3, 6))

        browser.close()
    print(f"\nDone. Saved {total} links to {OUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
