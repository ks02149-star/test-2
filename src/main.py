import sys
import os

# PyInstaller 강제 포함을 위한 명시적 임포트
try:
    import asyncio
    import _overlapped
except ImportError:
    pass

# Suppress harmless PyQt5 Qt QPA warnings caused by invalid OS fonts
os.environ["QT_LOGGING_RULES"] = "qt.qpa.fonts.warning=false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtGui import QFont, QFontDatabase

# Helper setup MUST run before UI loads
from src.utils.helpers import custom_excepthook, install_required_packages
sys.excepthook = custom_excepthook
install_required_packages()

# Load paths and global config
from src.config import FONT_DIR



def cleanup_before_exit():
    import subprocess
    try:
        # 남아있는 드라이버 프로세스를 강제로 종료하여 파일 잠금을 해제합니다.
        subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe", "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["taskkill", "/F", "/IM", "chromedriver_patched.exe", "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

def main():
    import multiprocessing
    multiprocessing.freeze_support()
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except AttributeError:
        pass 
        
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.aboutToQuit.connect(cleanup_before_exit)
    
    # 지연 로딩된 패치 적용
    from src.utils.helpers import patch_calendar
    patch_calendar()
    
    loaded_family = "SUIT"
    if os.path.exists(FONT_DIR):
        allowed_suffixes = ("regular.otf", "medium.otf", "semibold.otf", "bold.otf",
                            "regular.ttf", "medium.ttf", "semibold.ttf", "bold.ttf")
        for file_name in os.listdir(FONT_DIR):
            if file_name.lower().endswith(('.otf', '.ttf')):
                if any(suffix in file_name.lower() for suffix in allowed_suffixes):
                    font_path = os.path.join(FONT_DIR, file_name)
                    try:
                        with open(font_path, "rb") as f:
                            font_data = f.read()
                        font_id = QFontDatabase.addApplicationFontFromData(font_data)
                    except Exception:
                        font_id = -1
                        
                    if font_id != -1:
                        families = QFontDatabase.applicationFontFamilies(font_id)
                        if families and loaded_family != "SUIT":
                            loaded_family = families[0]
                            
    app_font = QFont(loaded_family, 10, QFont.Normal)
    app.setFont(app_font)


    # Import UI here to benefit from delayed loading
    from src.ui.login_dialog import LoginDialog

    # 프로세스 재시작 없이 내부 루프로 로그아웃/로그인 전환
    while True:
        app.wants_restart = False
        
        # 로그인 창은 Light 테마 기본값을 사용하도록 초기화
        from qfluentwidgets import setTheme, Theme, setThemeColor
        setTheme(Theme.LIGHT)
        setThemeColor('#009faa')
        
        login_dialog = LoginDialog()
        if login_dialog.exec_() == QDialog.Accepted:
            from src.ui.main_window import MainWindow
            window = MainWindow()
            window.show()
            
            # 메인 화면이 그려진 후 업데이트 체크 (UI 멈춤 방지)
            from src.utils.helpers import check_for_updates
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(500, lambda: check_for_updates(manual_check=False))
            
            app.exec_()
            
            if getattr(app, 'wants_restart', False):
                window.deleteLater()
                login_dialog.deleteLater()
                continue
            else:
                break
        else:
            break

    sys.exit(0)

if __name__ == '__main__':
    main()
