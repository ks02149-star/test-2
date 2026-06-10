import os
import sys

VERSION = "1.1"

# Base Path Logic
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # If config.py is inside src/, BASE_DIR should be the parent folder
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WORKSPACE_DIR = os.path.join(BASE_DIR, "Workspace")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "Data")
FONT_DIR = os.path.join(BASE_DIR, "Font")

SETTINGS_PATH = os.path.join(WORKSPACE_DIR, "settings.json")
CREDENTIALS_PATH = os.path.join(WORKSPACE_DIR, "credentials.json")
CONFIG_INI_PATH = os.path.join(DATA_DIR, "config.ini")
ERROR_LOG_PATH = os.path.join(WORKSPACE_DIR, "error_log.txt")

# Ensure required directories exist
os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# --- Global Session ---
SESSION = {
    "id": None,
    "name": None
}
