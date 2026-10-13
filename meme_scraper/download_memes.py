"""
Copies the original meme images listed in links.csv into meme_images/, untouched.
make_blank_templates.py then removes the captions from these copies.
Click Run in VS Code. Run reddit_scroll.py first so links.csv exists.
"""
from __future__ import annotations

import csv
import hashlib
import random
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

LINKS_FILE = Path("links.csv")
OUT_DIR = Path("meme_images")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}


def main():
    if not LINKS_FILE.exists():
        raise SystemExit("links.csv not found. Run reddit_scroll.py first (and open the meme_scraper folder in VS Code).")
    OUT_DIR.mkdir(exist_ok=True)
    with LINKS_FILE.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit("links.csv is empty. Lower MIN_SCORE / MIN_Q in reddit_scroll.py and run it again.")

    ok = 0
    for i, row in enumerate(rows, 1):
        url = row.get("content_url", "")
        if not url:
            continue
        suffix = Path(urlparse(url).path).suffix or ".jpg"
        dest = OUT_DIR / (hashlib.sha1(url.encode()).hexdigest()[:16] + suffix)
        if dest.exists():
            ok += 1
            continue
        try:
            r = requests.get(url, headers=UA, timeout=20)
            r.raise_for_status()
            if not r.headers.get("content-type", "").startswith("image"):
                print(f"[{i}] not an image: {url}")
                continue
            dest.write_bytes(r.content)
            ok += 1
            print(f"[{i:3d}/{len(rows)}] saved {dest.name}")
        except Exception as e:
            print(f"[{i}] failed {url}: {e}")
        time.sleep(random.uniform(0.3, 1.0))
    print(f"\nDone. {ok} images in {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
