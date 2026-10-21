"""
CircuitProof Top-Level Application Launcher (run.py)
Starts the FastAPI backend and serves the frontend Web Studio at http://127.0.0.1:8000
"""

import sys
from pathlib import Path
import uvicorn

ROOT_DIR = Path(__file__).resolve().parent
APP_DIR = ROOT_DIR / "backend" / "app"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

if __name__ == "__main__":
    print("=" * 65)
    print("  CircuitProof - AI Agentic Hardware Studio")
    print("  Web Studio:    http://127.0.0.1:8000")
    print("  API Docs:      http://127.0.0.1:8000/docs")
    print("  Legal & Lab:   http://127.0.0.1:8000/contact")
    print("=" * 65)
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=False)
