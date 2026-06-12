import os
import sys

VERSION = "1.1"

# Base Path Logic
if getattr(sys, 'frozen', False):
    # .exe 파일이 위치한 경로
    EXE_DIR = os.path.dirname(sys.executable)
    # PyInstaller --onefile 모드 내부 임시 압축해제 경로
    if hasattr(sys, '_MEIPASS'):
        INTERNAL_DIR = sys._MEIPASS
    else:
        INTERNAL_DIR = EXE_DIR
else:
    EXE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INTERNAL_DIR = EXE_DIR

WORKSPACE_DIR = os.path.join(EXE_DIR, "Workspace")
DATA_DIR = os.path.join(EXE_DIR, "Data")

ASSETS_DIR = os.path.join(INTERNAL_DIR, "assets")
FONT_DIR = os.path.join(INTERNAL_DIR, "Font")

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
