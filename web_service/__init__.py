"""FastAPI bridge for the existing desktop media engine."""

import sys
from pathlib import Path

# Import only the desktop package's Qt-free service modules, never its UI.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
