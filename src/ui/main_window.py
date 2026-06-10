from src.ui.interfaces.home_interface import HomeInterface
from src.ui.interfaces.schedule_interface import ScheduleInterface
from src.ui.interfaces.scraper_interface import ScraperInterface
from src.ui.interfaces.place_scraper_interface import PlaceScraperInterface
from src.ui.interfaces.company_list_interface import CompanyListInterface
from src.ui.interfaces.index_check_interface import IndexCheckInterface
from src.ui.interfaces.spell_check_interface import SpellCheckInterface
from src.ui.interfaces.setting_interface import SettingInterface

import os
import sys
import json
import time
import datetime
from datetime import date
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QUrl, QDate, QPropertyAnimation, QEasingCurve, QRect, QPoint, QMargins, QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QDialog, QFrame, QLabel, QStackedWidget, QGraphicsDropShadowEffect, QCalendarWidget, QPushButton, QFileDialog, QSizePolicy, QGridLayout
from PyQt5.QtGui import QFont, QFontDatabase, QDesktopServices, QTextCharFormat, QColor, QBrush, QPainter, QCursor, QPixmap
from qfluentwidgets import (PushButton, PrimaryPushButton, ComboBox, SpinBox, SwitchButton, TextEdit, 
                            setTheme, Theme, TitleLabel, SubtitleLabel, InfoBar, InfoBarPosition,
                            IndeterminateProgressRing, FluentWindow, FluentIcon, LineEdit,
                            TransparentToolButton, ScrollArea, CardWidget, MessageBox,
                            setThemeColor, NavigationItemPosition, qconfig, isDarkTheme,
                            BodyLabel, IconWidget, HyperlinkButton, PasswordLineEdit, CheckBox, NavigationPushButton, RoundMenu, Action)
from qfluentwidgets.common.icon import drawIcon
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, FONT_DIR, SETTINGS_PATH, CREDENTIALS_PATH

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        
        # Force Always Dark Mode
        setTheme(Theme.DARK)
        setThemeColor('#0078D4')
        
        self.init_window()
        
        self.home_interface = HomeInterface(self)
        self.schedule_interface = ScheduleInterface()
        self.scraper_interface = ScraperInterface(self)
        self.place_scraper_interface = PlaceScraperInterface(self)
        self.company_list_interface = CompanyListInterface(self)
        self.index_check_interface = IndexCheckInterface(self)
        self.spell_check_interface = SpellCheckInterface(self)
        self.settings_interface = SettingInterface(self)
        
        self.addSubInterface(self.home_interface, FluentIcon.HOME, '홈')
        self.addSubInterface(self.schedule_interface, getattr(FluentIcon, "CALENDAR", FluentIcon.DATE_TIME), "월간 일정표")
        self.addSubInterface(self.scraper_interface, FluentIcon.DOCUMENT, '블로그 순위 체크')
        self.addSubInterface(self.place_scraper_interface, getattr(FluentIcon, "POI", FluentIcon.SEARCH), '플레이스 순위 체크')
        self.addSubInterface(self.company_list_interface, FluentIcon.PEOPLE, '업체 리스트')
        self.addSubInterface(self.index_check_interface, getattr(FluentIcon, "PIE_SINGLE", FluentIcon.DOCUMENT), '지수 체크')
        self.addSubInterface(self.spell_check_interface, FluentIcon.EDIT, '맞춤법 검사기')
        self.addSubInterface(self.settings_interface, FluentIcon.SETTING, '설정', position=NavigationItemPosition.BOTTOM)
        
        self.navigationInterface.addItem('logout_btn', FluentIcon.POWER_BUTTON, '로그아웃', position=NavigationItemPosition.BOTTOM, onClick=self.handle_logout)
        qconfig.themeChanged.connect(self.update_theme_style)
        self.update_theme_style()
        
    def handle_logout(self):
        msg_box = MessageBox("로그아웃", "로그아웃 하시겠습니까?", self)
        if msg_box.exec_():
            global SESSION
            SESSION["id"] = None
            SESSION["name"] = None
            
            import os, sys, json
            base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            settings_path = os.path.join(base_dir, "Workspace", "settings.json")
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    data["auto_login"] = False
                    data.pop("saved_id", None)
                    data.pop("saved_pw", None)
                    with open(settings_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                except:
                    pass
                    
            from PyQt5.QtCore import QProcess
            QProcess.startDetached(sys.executable, sys.argv)
            QApplication.quit()

    def update_theme_style(self):
        is_dark = isDarkTheme()
        if is_dark:
            self.setStyleSheet("""
                MainWindow {
                    background-color: #161616;
                }
                NavigationPanel[menu=true], NavigationPanel[menu=false], NavigationPanel {
                    background-color: #161616 !important;
                    border: none !important;
                }
                StackedWidget {
                    background-color: #202020 !important;
                    border-top-left-radius: 10px !important;
                    border: 1px solid #2A2A2A !important;
                    border-right: none !important;
                    border-bottom: none !important;
                }
                QScrollArea, #ScrollContent, #scrollWidget {
                    border: none !important;
                    background-color: transparent !important;
                }
                CardWidget {
                    background-color: #2C2C2C !important;
                    border: 1px solid #3A3A3A !important;
                    border-radius: 10px !important;
                }
                TextEdit {
                    background-color: #161616 !important;
                    border: 1px solid #2C2C2C !important;
                    border-radius: 8px !important;
                }
            """)
        else:
            self.setStyleSheet("MainWindow { background-color: #F3F3F3; }")
        
    def init_window(self):
        self.setWindowTitle("푸름애드 관리 프로그램")
        self.resize(1400, 800)
        
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
 
    def closeEvent(self, event):
        if hasattr(self.scraper_interface, 'driver_worker') and self.scraper_interface.driver_worker.isRunning():
            self.scraper_interface.driver_worker.terminate()
            self.scraper_interface.driver_worker.wait()
            
        if hasattr(self.scraper_interface, 'worker') and self.scraper_interface.worker.isRunning():
            self.scraper_interface.worker.cleanup_drivers()
            self.scraper_interface.worker.terminate()
            self.scraper_interface.worker.wait()
            
        if hasattr(self.index_check_interface, 'worker') and self.index_check_interface.worker and self.index_check_interface.worker.isRunning():
            self.index_check_interface.worker.cleanup()
            self.index_check_interface.worker.terminate()
            self.index_check_interface.worker.wait()
            
        if hasattr(self, 'spell_check_interface') and hasattr(self.spell_check_interface, 'worker') and self.spell_check_interface.worker and self.spell_check_interface.worker.isRunning():
            self.spell_check_interface.worker.terminate()
            self.spell_check_interface.worker.wait()
            
        if hasattr(self, 'place_scraper_interface') and hasattr(self.place_scraper_interface, 'worker') and self.place_scraper_interface.worker and self.place_scraper_interface.worker.isRunning():
            self.place_scraper_interface.worker.cleanup_drivers()
            self.place_scraper_interface.worker.terminate()
            self.place_scraper_interface.worker.wait()
            
        event.accept()

