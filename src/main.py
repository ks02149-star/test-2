import sys
import os

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

def check_for_updates():
    # Keep the existing logic but gracefully fail since it's just a placeholder usually
    pass

def main():
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except AttributeError:
        pass 
        
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    
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

    check_for_updates()

    # Import UI here to benefit from delayed loading
    from src.ui.login_dialog import LoginDialog
    from src.ui.main_window import MainWindow

    login_dialog = LoginDialog()
    if login_dialog.exec_() == QDialog.Accepted:
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
