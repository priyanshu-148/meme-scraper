"""Shared filter helpers."""
from __future__ import annotations
import re
from pathlib import Path

from PIL import Image

FUNNY_KEYWORDS = [
    "funny", "lol", "dank", "meme", "haha", "laugh", "hilarious", "joke",
    "comedic", "sarcasm", "silly", "relatable", "kek", "sussy", "irl",
]
FUNNY_SUBREDDITS = {
    "memes", "dankmemes", "funny", "me_irl", "wholesomememes", "memeeconomy",
    "comedyheaven", "terriblefacebookmemes", "2meirl4meirl", "programmerhumor",
}

# Whole-word match so "lol" doesn't match inside unrelated words
_KW_RE = re.compile(r"\b(" + "|".join(map(re.escape, FUNNY_KEYWORDS)) + r")\b", re.I)


def looks_like_funny(title: str, community: str | None = None) -> bool:
    if community and community.lower() in FUNNY_SUBREDDITS:
        return True
    return bool(_KW_RE.search(title or ""))


def passes_content_filter(img_path: Path, min_bytes: int = 5_000, min_side: int = 200) -> bool:
    """File exists, isn't tiny, and is a valid image of reasonable size."""
    try:
        if img_path.stat().st_size < min_bytes:
            return False
        with Image.open(img_path) as im:
            w, h = im.size
            im.verify()
        return w >= min_side and h >= min_side
    except Exception:
        return False
