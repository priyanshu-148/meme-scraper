"""Run once (click Run) to install the AI packages for make_blank_templates.py. Takes a few minutes."""
import subprocess
import sys
from pathlib import Path

req = Path(__file__).parent / "requirements_ai.txt"
subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req)])
print("\nAll done. Now run make_blank_templates.py")
