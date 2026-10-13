"""
1) Downloads the blank meme templates from Imgflip (free, no key).
2) Downloads the meme images listed in links.csv (made by reddit_scroll.py).
3) Guesses which template each meme uses and writes matches.csv + template_stats.csv.

Just click Run in VS Code. Run reddit_scroll.py first so links.csv exists.
"""
from __future__ import annotations

import csv
import hashlib
import random
import re
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image

# ======== SETTINGS ========
LINKS_FILE = Path("links.csv")
TEMPLATE_DIR = Path("templates")
MEME_DIR = Path("meme_images")
MATCH_THRESHOLD = 35      # lower = stricter. Distance is 0-255; check matches.csv and tune
DOWNLOAD_MEMES = True
# ==========================

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def fetch(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        r = requests.get(url, headers=UA, timeout=20)
        r.raise_for_status()
        if not r.headers.get("content-type", "").startswith("image"):
            return False
        dest.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"[warn] {url}: {e}")
        return False


def signature(path: Path) -> list[int] | None:
    try:
        with Image.open(path) as im:
            return list(im.convert("L").resize((16, 16)).getdata())
    except Exception:
        return None


def distance(a: list[int], b: list[int]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def get_templates() -> list[dict]:
    TEMPLATE_DIR.mkdir(exist_ok=True)
    print("Fetching template list from Imgflip...")
    data = requests.get("https://api.imgflip.com/get_memes", headers=UA, timeout=20).json()
    if not data.get("success"):
        raise SystemExit("Imgflip request failed")
    out = []
    for m in data["data"]["memes"]:
        ext = Path(urlparse(m["url"]).path).suffix or ".jpg"
        path = TEMPLATE_DIR / f"{m['id']}{ext}"
        if fetch(m["url"], path):
            out.append({"id": m["id"], "name": m["name"], "path": path,
                        "sig": signature(path), "boxes": m.get("box_count", "")})
    with (TEMPLATE_DIR / "templates.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "file", "box_count"])
        for t in out:
            w.writerow([t["id"], t["name"], t["path"].name, t["boxes"]])
    print(f"{len(out)} templates saved in {TEMPLATE_DIR}/")
    return out


def match(title: str, sig: list[int] | None, templates: list[dict]) -> tuple[str, float, str]:
    nt = norm(title)
    for t in templates:                      # 1) template name appears in the title
        n = norm(t["name"])
        if len(n) >= 8 and n in nt:
            return t["name"], 0.0, "title"
    if sig is None:
        return "", 255.0, "none"
    best = min(templates, key=lambda t: distance(sig, t["sig"]) if t["sig"] else 255)  # 2) look-alike
    d = distance(sig, best["sig"]) if best["sig"] else 255.0
    return best["name"], d, "image"


def main():
    if not LINKS_FILE.exists():
        alt = Path(__file__).parent / "links.csv"
        if alt.exists():
            globals()["LINKS_FILE"] = alt
        else:
            raise SystemExit("links.csv not found. Run reddit_scroll.py first.")

    templates = get_templates()
    MEME_DIR.mkdir(exist_ok=True)

    with LINKS_FILE.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    print(f"{len(rows)} links to process")

    results = []
    for i, row in enumerate(rows, 1):
        url = row.get("content_url", "")
        img_path = None
        if DOWNLOAD_MEMES and url:
            suffix = Path(urlparse(url).path).suffix or ".jpg"
            img_path = MEME_DIR / (hashlib.sha1(url.encode()).hexdigest()[:16] + suffix)
            if not img_path.exists():
                time.sleep(random.uniform(0.3, 1.0))
            if not fetch(url, img_path):
                img_path = None
        sig = signature(img_path) if img_path else None
        name, dist, how = match(row.get("title", ""), sig, templates)
        confident = how == "title" or dist <= MATCH_THRESHOLD
        results.append({**row, "image_file": str(img_path or ""), "template": name if confident else "",
                        "best_guess": name, "distance": round(dist, 1), "method": how,
                        "confident": confident})
        print(f"[{i:3d}] {'OK ' if confident else '?? '} {name[:30]:30} d={dist:5.1f} | {row.get('title','')[:40]}")

    if results:
        with open("matches.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            w.writeheader()
            w.writerows(results)

    stats = defaultdict(lambda: {"count": 0, "score": 0, "q": 0.0})
    for r in results:
        if r["confident"]:
            s = stats[r["template"]]
            s["count"] += 1
            s["score"] += int(r.get("score") or 0)
            s["q"] += float(r.get("q_per_hour") or 0)
    ranked = sorted(stats.items(), key=lambda kv: kv[1]["score"], reverse=True)
    with open("template_stats.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["template", "memes", "total_score", "avg_q_per_hour"])
        for name, s in ranked:
            w.writerow([name, s["count"], s["score"], round(s["q"] / s["count"], 1)])

    print("\nTop templates by total upvotes:")
    for name, s in ranked[:15]:
        print(f"  {name:35} {s['count']:3d} memes  {s['score']:>8} pts")
    print("\nSaved matches.csv and template_stats.csv. Rows with confident=False are guesses.")


if __name__ == "__main__":
    main()
