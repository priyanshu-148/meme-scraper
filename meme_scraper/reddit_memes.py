"""Reddit meme scraper using the official API (PRAW). Most reliable option."""
import json
import logging
import os
import time
from pathlib import Path

import praw
import requests
from dotenv import load_dotenv

from filters import passes_content_filter

load_dotenv()

# ======== SETTINGS ========
# Paste your Reddit app credentials here (from reddit.com/prefs/apps)
CLIENT_ID = ""
CLIENT_SECRET = ""
USER_AGENT = "memescraper/1.0 by u/your_reddit_username"

SUBREDDITS = ["memes", "dankmemes", "funny", "wholesomememes"]
POST_LIMIT = 100          # per subreddit
SORT = "hot"              # "hot", "new", or "top"
TOP_TIME_FILTER = "week"  # only used when SORT = "top": hour/day/week/month/year/all
SKIP_NSFW = True
OUT_DIR = Path("reddit_memes")
# ==========================

META_FILE = OUT_DIR / "metadata.jsonl"
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("reddit_memes")


def make_client() -> praw.Reddit:
    cid = CLIENT_ID or os.getenv("REDDIT_CLIENT_ID")
    secret = CLIENT_SECRET or os.getenv("REDDIT_CLIENT_SECRET")
    if not cid or not secret:
        raise SystemExit("Paste your CLIENT_ID and CLIENT_SECRET at the top of reddit_memes.py")
    reddit = praw.Reddit(
        client_id=cid,
        client_secret=secret,
        user_agent=USER_AGENT,
    )
    reddit.read_only = True
    return reddit


def listing(reddit, sub):
    s = reddit.subreddit(sub)
    if SORT == "new":
        return s.new(limit=POST_LIMIT)
    if SORT == "top":
        return s.top(time_filter=TOP_TIME_FILTER, limit=POST_LIMIT)
    return s.hot(limit=POST_LIMIT)


def download(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=15, stream=True, headers={"User-Agent": "memescraper/1.0"})
        r.raise_for_status()
        if not r.headers.get("content-type", "").startswith("image"):
            return False
        with dest.open("wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        log.warning("download failed %s: %s", url, e)
        return False


def load_seen() -> set[str]:
    seen = set()
    if META_FILE.exists():
        for line in META_FILE.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(json.loads(line)["id"])
            except Exception:
                pass
    return seen


def main():
    OUT_DIR.mkdir(exist_ok=True)
    reddit = make_client()
    seen = load_seen()
    saved = 0

    with META_FILE.open("a", encoding="utf-8") as meta:
        for sub in SUBREDDITS:
            log.info("Fetching r/%s (%s)", sub, SORT)
            for post in listing(reddit, sub):
                if post.id in seen or post.stickied:
                    continue
                if SKIP_NSFW and post.over_18:
                    continue
                ext = Path(post.url.split("?")[0]).suffix.lower()
                if ext not in IMAGE_EXTS:
                    continue

                path = OUT_DIR / f"{post.id}{ext}"
                if not download(post.url, path):
                    continue
                if not passes_content_filter(path):
                    path.unlink(missing_ok=True)
                    continue

                meta.write(json.dumps({
                    "id": post.id,
                    "title": post.title,
                    "author": str(post.author),
                    "subreddit": post.subreddit.display_name,
                    "score": post.score,
                    "num_comments": post.num_comments,
                    "created_utc": post.created_utc,
                    "url": post.url,
                    "permalink": f"https://reddit.com{post.permalink}",
                    "image_path": str(path),
                }) + "\n")
                meta.flush()
                seen.add(post.id)
                saved += 1
                log.info("saved %s | %s", post.id, post.title[:50])
                time.sleep(0.3)

    log.info("Done. %d new images in %s/", saved, OUT_DIR)


if __name__ == "__main__":
    main()
