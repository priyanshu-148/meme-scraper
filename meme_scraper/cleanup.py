"""
Deletes everything the scraper made (links, downloaded memes, blank templates, reports)
so you can start fresh each day. It never touches your .py files.
Click Run in VS Code.
"""
from __future__ import annotations

import shutil
from pathlib import Path

# ======== SETTINGS ========
ASK_FIRST = True          # asks "yes/no" before deleting. Set False for no prompt.
KEEP_BLANK_TEMPLATES = False   # True = keep the finished blank_templates/ folder
# ==========================

FOLDERS = ["meme_images", "templates", "images", "reddit_memes"]
FILES = ["links.csv", "matches.csv", "template_stats.csv", "metadata.jsonl"]
if not KEEP_BLANK_TEMPLATES:
    FOLDERS.append("blank_templates")


def size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def main():
    roots = {Path.cwd().resolve(), Path(__file__).parent.resolve()}
    targets = []
    for root in roots:
        for name in FOLDERS:
            p = root / name
            if p.is_dir():
                targets.append(p)
        for name in FILES:
            p = root / name
            if p.is_file():
                targets.append(p)

    if not targets:
        print("Nothing to clean up.")
        return

    total = sum(size(p) for p in targets)
    print("Will delete:")
    for p in targets:
        print(f"  {p}")
    print(f"Total: {total / 1e6:.1f} MB")

    if ASK_FIRST and input("\nDelete these? (yes/no): ").strip().lower() not in {"y", "yes"}:
        print("Cancelled. Nothing deleted.")
        return

    for p in targets:
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    print(f"Done. Freed {total / 1e6:.1f} MB.")


if __name__ == "__main__":
    main()
