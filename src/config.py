import os
import sys

VERSION = "1.3.1"

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
import os
import sys

VERSION = "1.3.1"

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
    "name": None,
    "is_admin": False
}

# --- Google Sheets Config ---
SPREADSHEET_ID = "1wWLxMTY3D5urtn0gomepgA1blQnyz05BUi2wepWBTDk"

# 구글 스프레드시트 및 드라이브 폴더 설정
APPROVAL_SPREADSHEET_ID = "1yPzW3mJZnZScGAZq8stxf7obpXeCcweIe9Ssb2NKn1M" # 전자결재 RAW DATA
TEMPLATE_LEAVE_REQUEST_ID = "1kq3mBjh_ksRlVbbx97ajBk-78OhQhe-qUoR9991dws4" # 연차휴가신청서 양식
ROOT_LEAVE_HISTORY_FOLDER_ID = "16KOlr9JfBvaBPTMdIMrR6djYgtFSpXnv" # 연반차 사용 내역 폴더
APPROVAL_IMAGE_FOLDER_ID = "1t4LX0Xsm-W9iFwQVZmvSLqlcgToPjs4M"
STAMP_FOLDER_ID = "1t4LX0Xsm-W9iFwQVZmvSLqlcgToPjs4M"
GAS_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyhP14CpFWfEAITeyGxXU0b9TInLvTeofAIa7ZSe8lIPrsPSs8zhh2WUDX3LSCTNC4iNg/exec" # 구글 앱스 스크립트 웹앱 URL (파일 대리 복사용)
