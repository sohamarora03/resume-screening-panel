"""Force the offline demo engine for tests so they never call a paid API."""
import os
import sys
from pathlib import Path

os.environ["DEMO_MODE"] = "true"
os.environ["DEMO_DELAY"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
