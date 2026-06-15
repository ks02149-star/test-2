import requests
from packaging.version import parse as parse_version
from src.config import VERSION
def perform_update(release_info=None):
    if not release_info:
        return
        
    import os, sys, tempfile, subprocess
    import requests
    from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QApplication
    from PyQt5.QtCore import Qt

    if not getattr(sys, 'frozen', False):
        import webbrowser
        QMessageBox.information(None, "안내", "개발 환경에서는 자동 업데이트가 지원되지 않습니다.\n다운로드 페이지로 이동합니다.")
        webbrowser.open(release_info.get("html_url", "https://github.com/ks02149-star/test-2/releases/latest"))
        return

    # 1. 릴리즈에서 .exe 파일 URL 찾기
    download_url = None
    assets = release_info.get("assets", [])
    for asset in assets:
        if asset.get("name", "").endswith(".exe"):
            download_url = asset.get("browser_download_url")
            break
            
    if not download_url:
        QMessageBox.critical(None, "오류", "최신 릴리즈에서 설치 파일(.exe)을 찾을 수 없습니다.")
        return

    # 2. 다운로드 및 진행률 표시
    try:
        progress = QProgressDialog("최신 버전을 다운로드 중입니다...", "취소", 0, 100, None)
        progress.setWindowTitle("업데이트")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        temp_dir = tempfile.gettempdir()
        new_exe_path = os.path.join(temp_dir, "update_new.exe")
        
        downloaded_size = 0
        with open(new_exe_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1048576): # 1MB 단위로 큼직하게 받아 다운로드 속도 대폭 향상 (서버 끊김 방지)
                if progress.wasCanceled():
                    return
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        percent = int((downloaded_size / total_size) * 100)
                        progress.setValue(percent)
                    QApplication.processEvents()
                    
        # 깃허브 서버 문제나 인터넷 불안정으로 파일이 중간에 끊긴 채 다운로드 완료 처리되는 것을 원천 차단
        if total_size > 0 and downloaded_size < total_size:
            raise Exception(f"다운로드가 중간에 끊겼습니다. (받은 용량: {downloaded_size} / 전체: {total_size})\\n다시 시도해주세요.")
            
        progress.setValue(100)

        # 3. 덮어쓰기용 배치 스크립트 생성 및 실행
        current_exe = sys.executable
        pid = os.getpid()
        meipass = getattr(sys, '_MEIPASS', '')
        bat_path = os.path.join(temp_dir, "update_script.bat")
        
        with open(bat_path, "w", encoding="mbcs") as f:
            f.write('@echo off\n')
            f.write('setlocal enabledelayedexpansion\n')
            f.write('timeout /t 1 /nobreak > nul\n')
            f.write('set max_retries=15\n')
            f.write('set count=0\n')
            f.write(':retry\n')
            f.write(f'copy /y "{new_exe_path}" "{current_exe}" > nul 2>&1\n')
            f.write('if %errorlevel% neq 0 (\n')
            f.write('    set /a count+=1\n')
            f.write('    if !count! geq %max_retries% goto fail\n')
            f.write('    timeout /t 1 /nobreak > nul\n')
            f.write('    goto retry\n')
            f.write(')\n')
            
            # 기존 프로세스가 찌꺼기(반쯤 지워진 임시 폴더)를 남기고 죽는 PyInstaller 버그 원천 차단
            # 구버전이 쓰던 MEI 임시 폴더 경로를 추적하여 스크립트가 직접 강제로 박살냄
            f.write('timeout /t 2 /nobreak > nul\n')
            if meipass:
                f.write(f'rmdir /s /q "{meipass}" > nul 2>&1\n')
                
            f.write(f'start "" "{current_exe}"\n')
            f.write('goto cleanup\n')
            f.write(':fail\n')
            f.write(f'start "" "{current_exe}"\n')
            f.write(':cleanup\n')
            f.write(f'del "{new_exe_path}"\n')
            f.write('del "%~f0"\n')
            
        # 경로 띄어쓰기 인식 오류를 원천 차단하기 위해 리스트 형태로 전달
        subprocess.Popen([bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
        
        # 일반 종료(sys.exit) 시 임시 폴더를 삭제하느라 시간이 끌리고, 
        # 삭제 도중 새 프로그램이 켜지면 DLL 파일이 깨지는 현상이 발생하므로 즉시 강제 종료(os._exit) 사용
        os._exit(0)
        
    except Exception as e:
        QMessageBox.critical(None, "다운로드 오류", f"업데이트 파일을 받는 중 오류가 발생했습니다:\n{str(e)}")
import sys
import os
import traceback
import subprocess
from src.config import WORKSPACE_DIR

def custom_excepthook(exc_type, exc_value, exc_tb):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    
    # 1. 오류 내용을 Workspace 디렉토리 내에 강제 저장
    try:
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        workspace_dir = os.path.join(base_dir, "Workspace")
        os.makedirs(workspace_dir, exist_ok=True)
        log_path = os.path.join(workspace_dir, "error_log.txt")
        
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(error_msg)
    except:
        pass
        
    # 2. 콘솔의 input() 대신 GUI 팝업창(QMessageBox)으로 오류 출력
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        if QApplication.instance():
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("치명적 오류 발생")
            msg_box.setText("프로그램 실행 중 오류가 발생하여 종료됩니다.\n'Workspace' 폴더에 생성된 'error_log.txt'를 확인해주세요.")
            msg_box.setDetailedText(error_msg)
            msg_box.exec_()
    except:
        pass

sys.excepthook = custom_excepthook

def install_required_packages():
    if getattr(sys, 'frozen', False):
        return
        
    packages = {
        "pandas": "pandas", 
        "selenium": "selenium", 
        "webdriver-manager": "webdriver_manager", 
        "openpyxl": "openpyxl",
        "PyQt5": "PyQt5",
        "PyQtWebEngine": "PyQt5.QtWebEngineWidgets",
        "PyQt-Fluent-Widgets": "qfluentwidgets",
        "gspread": "gspread",
        "oauth2client": "oauth2client"
    }
    if os.name == 'nt':
        packages["pywin32"] = "win32api"
        
    for pip_name, import_name in packages.items():
        try:
            __import__(import_name)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])

install_required_packages()

import qfluentwidgets.components.date_time.calendar_view as cv
orig_init = cv.DayScrollView.__init__

def new_init(self, parent=None):
    orig_init(self, parent)
    self.weekDays = [self.tr('Su'), self.tr('Mo'), self.tr('Tu'), self.tr('We'),
                     self.tr('Th'), self.tr('Fr'), self.tr('Sa')]
    while self.weekDayLayout.count():
        item = self.weekDayLayout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    for day in self.weekDays:
        label = cv.QLabel(day)
        label.setObjectName('weekDayLabel')
        self.weekDayLayout.addWidget(label, 1, cv.Qt.AlignHCenter)

def new_initItems(self):
    self.clear()
    startDate = cv.QDate(self.minYear, 1, 1)
    endDate = cv.QDate(self.maxYear, 12, 31)
    currentDate = startDate

    bias = currentDate.dayOfWeek() % 7
    for i in range(bias):
        item = cv.QListWidgetItem(self)
        item.setFlags(cv.Qt.NoItemFlags)
        self.addItem(item)

    items, dates = [], []
    while currentDate <= endDate:
        items.append(str(currentDate.day()))
        dates.append(cv.QDate(currentDate))
        currentDate = currentDate.addDays(1)
        
    self.addItems(items)
    for i, date in enumerate(dates):
        self.item(i + bias).setData(cv.Qt.UserRole, date)

def new_dateToRow(self, date: cv.QDate):
    startDate = cv.QDate(self.minYear, 1, 1)
    days = startDate.daysTo(date)
    return days + (startDate.dayOfWeek() % 7)

cv.DayScrollView.__init__ = new_init

def check_for_updates(manual_check=False):
    try:
        response = requests.get("https://api.github.com/repos/ks02149-star/test-2/releases/latest", timeout=10)
        response.raise_for_status()
        latest_release = response.json()
        latest_tag = latest_release.get("tag_name", "")
        
        if parse_version(latest_tag) > parse_version(VERSION):
            from PyQt5.QtWidgets import QMessageBox
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("업데이트 알림")
            msg_box.setText("새로운 버전이 확인되었습니다. 업데이트 하시겠습니까?")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            if msg_box.exec_() == QMessageBox.Yes:
                perform_update(latest_release)
        else:
            if manual_check:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(None, "업데이트", "현재 최신 버전을 사용 중입니다.")
    except requests.exceptions.Timeout:
        if manual_check:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(None, "응답 지연", "업데이트 서버 응답이 지연되고 있습니다.\n잠시 후 다시 시도해주세요.")
    except Exception as e:
        if manual_check:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(None, "오류", f"업데이트 확인 중 오류가 발생했습니다:\n{str(e)}\n\n인터넷 연결 상태를 확인해주세요.")

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLabel, QFrame, QDialog, QMessageBox)
from qfluentwidgets import (TitleLabel, SubtitleLabel, ComboBox, PushButton, 
                            PrimaryPushButton, LineEdit, InfoBar, ScrollArea)
from calendar import monthrange


import json
from src.config import DATA_DIR

def load_companies():
    path = os.path.join(DATA_DIR, 'companies.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return [{'name':'임시 업체 1','homepage':'https://www.naver.com','place':'','blog1':'https://blog.naver.com','blog2':'','instagram':'https://www.instagram.com'}]

def save_companies(companies):
    path = os.path.join(DATA_DIR, 'companies.json')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(companies, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False



def get_holiday_checks_file_path():
    from src.config import DATA_DIR
    import os
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, 'holiday_checks.json')

def load_holiday_checks():
    path = get_holiday_checks_file_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_holiday_checks(data):
    path = get_holiday_checks_file_path()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False

def get_korean_holidays(year):
    holidays = {
        f"{year}-01-01": "신정",
        f"{year}-03-01": "삼일절",
        f"{year}-05-05": "어린이날",
        f"{year}-06-06": "현충일",
        f"{year}-07-17": "제헌절",
        f"{year}-08-15": "광복절",
        f"{year}-10-03": "개천절",
        f"{year}-10-09": "한글날",
        f"{year}-12-25": "성탄절"
    }
    
    if year == 2024:
        holidays.update({
            "2024-02-09": "설날 연휴",
            "2024-02-10": "설날",
            "2024-02-11": "설날 연휴",
            "2024-02-12": "설날 대체공휴일",
            "2024-04-10": "제22대 국회의원 선거",
            "2024-05-06": "어린이날 대체공휴일",
            "2024-05-15": "부처님오신날",
            "2024-09-16": "추석 연휴",
            "2024-09-17": "추석",
            "2024-09-18": "추석 연휴"
        })
    elif year == 2025:
        holidays.update({
            "2025-01-27": "임시공휴일",
            "2025-01-28": "설날 연휴",
            "2025-01-29": "설날",
            "2025-01-30": "설날 연휴",
            "2025-03-03": "삼일절 대체공휴일",
            "2025-05-06": "어린이날 및 부처님오신날 대체공휴일",
            "2025-10-05": "추석 연휴",
            "2025-10-06": "추석",
            "2025-10-07": "추석 연휴",
            "2025-10-08": "추석 대체공휴일"
        })
    elif year == 2026:
        holidays.update({
            "2026-02-16": "설날 연휴",
            "2026-02-17": "설날",
            "2026-02-18": "설날 연휴",
            "2026-03-02": "삼일절 대체공휴일",
            "2026-05-24": "부처님오신날",
            "2026-05-25": "부처님오신날 대체공휴일",
            "2026-06-03": "제9회 전국동시지방선거",
            "2026-08-17": "광복절 대체공휴일",
            "2026-09-24": "추석 연휴",
            "2026-09-25": "추석",
            "2026-09-26": "추석 연휴",
            "2026-09-28": "추석 대체공휴일",
            "2026-10-05": "개천절 대체공휴일"
        })
    elif year == 2027:
        holidays.update({
            "2027-02-06": "설날 연휴",
            "2027-02-07": "설날",
            "2027-02-08": "설날 연휴",
            "2027-02-09": "설날 대체공휴일",
            "2027-05-13": "부처님오신날",
            "2027-07-19": "제헌절 대체공휴일",
            "2027-08-16": "광복절 대체공휴일",
            "2027-09-14": "추석 연휴",
            "2027-09-15": "추석",
            "2027-09-16": "추석 연휴",
            "2027-10-04": "개천절 대체공휴일",
            "2027-10-11": "한글날 대체공휴일",
            "2027-12-27": "성탄절 대체공휴일"
        })
    elif year == 2028:
        holidays.update({
            "2028-01-26": "설날 연휴",
            "2028-01-27": "설날",
            "2028-01-28": "설날 연휴",
            "2028-04-12": "제23대 국회의원 선거",
            "2028-05-02": "부처님오신날",
            "2028-09-30": "추석 연휴",
            "2028-10-01": "추석 연휴",
            "2028-10-02": "추석",
            "2028-10-04": "추석 대체공휴일",
            "2028-10-05": "대체공휴일"
        })
    return holidays

