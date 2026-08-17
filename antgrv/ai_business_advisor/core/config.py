import os
import sys
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Database Paths
DB_PATH = DATA_DIR / "app.db"
VECTOR_STORE_PATH = DATA_DIR / "vector_store"
LEX_CACHE_PATH = DATA_DIR / "lex_cache"

# Ensure subdirectories exist
os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
os.makedirs(LEX_CACHE_PATH, exist_ok=True)

# UI Settings
APP_NAME = "AI Business Advisor Uzbekistan"
APP_VERSION = "1.0.0"
THEME = "dark" # Enforce dark theme

# AI Settings
DEFAULT_AI_PROVIDER = "g4f" # Default to GPT4Free
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30

# Colors for UI (Ultra Dark Premium)
COLORS = {
    "background": "#0d1117",
    "surface": "#161b22",
    "surface_hover": "#21262d",
    "primary": "#2f81f7",
    "primary_hover": "#388bfd",
    "text": "#c9d1d9",
    "text_muted": "#8b949e",
    "border": "#30363d",
    "success": "#2ea043",
    "warning": "#d29922",
    "error": "#f85149",
}
