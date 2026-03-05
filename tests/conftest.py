import os
import sys
from pathlib import Path


BACKEND_PATH = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_PATH) not in sys.path:
  sys.path.insert(0, str(BACKEND_PATH))

# backend/app.py mounts "static" using a relative path at import time.
os.chdir(BACKEND_PATH)
