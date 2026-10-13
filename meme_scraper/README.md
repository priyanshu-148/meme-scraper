# Meme Scraper (VS Code, no terminal)

1. In VS Code: File > Open Folder > pick `meme_scraper`. Install the "Python" extension if prompted.
2. Open `install.py` and click the Run (play) button at the top right. Do this once.
3. Reddit API script (recommended):
   - Go to https://www.reddit.com/prefs/apps > "create another app" > type **script**, redirect URI `http://localhost:8080`.
   - Paste the client ID (under the app name) and secret into the top of `reddit_memes.py`.
   - Open `reddit_memes.py` and click Run.
4. Browser script (uses your installed Chrome, no API key): open `explore_scrape.py` and click Run.
   Set `HEADLESS = False` at the top if you want to watch Chrome work.

Images land in `reddit_memes/` (API script) or `images/` (browser script), next to a `metadata.jsonl`.
Settings (subreddits, limits, URL) are at the top of each script.
