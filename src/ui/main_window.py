from src.ui.interfaces.home_interface import HomeInterface
from src.ui.interfaces.schedule_interface import ScheduleInterface
from src.ui.interfaces.scraper_interface import ScraperInterface
from src.ui.interfaces.place_scraper_interface import PlaceScraperInterface
from src.ui.interfaces.company_list_interface import CompanyListInterface
from src.ui.interfaces.holiday_check_interface import HolidayCheckInterface
from src.ui.interfaces.index_check_interface import IndexCheckInterface
from src.ui.interfaces.spell_check_interface import SpellCheckInterface
from src.ui.interfaces.setting_interface import SettingInterface
from src.ui.interfaces.authority_test_interface import AuthorityTestInterface
from src.ui.interfaces.approval_request_interface import ApprovalRequestInterface
from src.ui.interfaces.approval_check_interface import ApprovalCheckInterface
from src.ui.interfaces.approval_manage_interface import ApprovalManageInterface

import os
import sys
import json
import time
import datetime
from datetime import date
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QUrl, QDate, QPropertyAnimation, QEasingCurve, QRect, QPoint, QMargins, QTimer, QEvent
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QDialog, QFrame, QLabel, QStackedWidget, QGraphicsDropShadowEffect, QCalendarWidget, QPushButton, QFileDialog, QSizePolicy, QGridLayout, QGraphicsOpacityEffect
from PyQt5.QtGui import QFont, QFontDatabase, QDesktopServices, QTextCharFormat, QColor, QBrush, QPainter, QCursor, QPixmap
from qfluentwidgets import (PushButton, PrimaryPushButton, ComboBox, SpinBox, SwitchButton, TextEdit, 
                            setTheme, Theme, TitleLabel, SubtitleLabel, InfoBar, InfoBarPosition,
                            IndeterminateProgressRing, FluentWindow, FluentIcon, LineEdit,
                            TransparentToolButton, ScrollArea, CardWidget, MessageBox,
                            setThemeColor, NavigationItemPosition, qconfig, isDarkTheme,
                            BodyLabel, IconWidget, HyperlinkButton, PasswordLineEdit, CheckBox, NavigationPushButton, RoundMenu, Action)
from qfluentwidgets.common.icon import drawIcon
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, FONT_DIR, SETTINGS_PATH, CREDENTIALS_PATH
from src.utils.helpers import safe_json_load, safe_json_save

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        
        # Force Always Dark Mode
        setTheme(Theme.DARK)
        setThemeColor('#0078D4')
        
        self.init_window()
        
        self.home_interface = HomeInterface(self)
        self.schedule_interface = ScheduleInterface(self)
        self.scraper_interface = ScraperInterface(self)
        self.place_scraper_interface = PlaceScraperInterface(self)
        self.company_list_interface = CompanyListInterface(self)
        self.holiday_check_interface = HolidayCheckInterface(self)
        self.index_check_interface = IndexCheckInterface(self)
        self.spell_check_interface = SpellCheckInterface(self)
        self.authority_test_interface = AuthorityTestInterface(self)
        self.settings_interface = SettingInterface(self)
        
        self.addSubInterface(self.home_interface, FluentIcon.HOME, '홈')
        self.addSubInterface(self.schedule_interface, getattr(FluentIcon, "CALENDAR", FluentIcon.DATE_TIME), "월간 일정표")
        self.addSubInterface(self.company_list_interface, FluentIcon.PEOPLE, '업체 리스트')
        self.addSubInterface(self.holiday_check_interface, getattr(FluentIcon, "CHECKBOX", FluentIcon.ACCEPT), '업체별 휴진 체크')
        self.addSubInterface(self.scraper_interface, FluentIcon.DOCUMENT, '블로그 순위 체크')
        self.addSubInterface(self.place_scraper_interface, getattr(FluentIcon, "POI", FluentIcon.SEARCH), '플레이스 순위 체크')
        self.addSubInterface(self.index_check_interface, getattr(FluentIcon, "PIE_SINGLE", FluentIcon.DOCUMENT), '블로그 통계 대시보드')
        self.addSubInterface(self.spell_check_interface, FluentIcon.EDIT, '맞춤법 검사기')
        self.addSubInterface(self.authority_test_interface, getattr(FluentIcon, "SHIELD", FluentIcon.INFO), '권한테스트')
        
        # 전자결재 시스템 추가
        self.approval_request_interface = ApprovalRequestInterface(self)
        self.approval_check_interface = ApprovalCheckInterface(self)
        self.addSubInterface(self.approval_request_interface, FluentIcon.EDIT, '전자결재')
        self.addSubInterface(self.approval_check_interface, FluentIcon.HISTORY, '내 결재 확인')
        
        # 관리자 전용 '결재관리'
        if SESSION.get('id') in ['hyuni3966', '테스트3']:
            self.approval_manage_interface = ApprovalManageInterface(self)
            self.addSubInterface(self.approval_manage_interface, getattr(FluentIcon, "PEOPLE", FluentIcon.SEARCH), '결재관리')
            
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
            
            data = safe_json_load(SETTINGS_PATH, default={})
            data["auto_login"] = False
            data.pop("saved_id", None)
            data.pop("saved_pw", None)
            safe_json_save(SETTINGS_PATH, data)
                    
            # 새로운 프로세스를 띄우는 대신, 내부 루프로 넘기기 위한 플래그 설정
            QApplication.instance().wants_restart = True
            QApplication.quit()

    def load_theme(self):
        config_path = os.path.join(WORKSPACE_DIR, "settings.json")
        data = safe_json_load(config_path, default={})
        if data:
            theme_val = data.get('theme', 'Auto')
            if theme_val == 'Light':
                setTheme(Theme.LIGHT)
            elif theme_val == 'Dark':
                setTheme(Theme.DARK)
            else:
                setTheme(Theme.AUTO)

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
                TextEdit, LineEdit, ComboBox {
                    background-color: #161616 !important;
                    border: 1px solid #2C2C2C !important;
                    border-radius: 8px !important;
                    color: white !important;
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



