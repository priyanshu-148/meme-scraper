"""Run this once (click the Run button in VS Code) to install everything."""
import subprocess
import sys
from pathlib import Path

req = Path(__file__).parent / "requirements.txt"
subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req)])
print("\nAll done. You can now run reddit_memes.py or explore_scrape.py")
