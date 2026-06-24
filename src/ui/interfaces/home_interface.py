
from src.config import VERSION
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
from src.ui.components.cards import FeatureCard, MonthlyScheduleSummaryCard
from src.core.scraper_threads import NewsWorker
from src.core.schedule_threads import ScheduleFetchThread
from src.ui.components.home_view import HomeViewWidget
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, FONT_DIR, SETTINGS_PATH, CREDENTIALS_PATH

class HomeInterface(ScrollArea):
    def __init__(self, main_window, parent=None):
        super().__init__(parent=parent)
        self.main_window = main_window
        self.setObjectName("HomeInterface")
        
        # Determine time of day
        hour = datetime.datetime.now().hour
        bg_image_name = "bg_night.png"
        user_name = SESSION.get('name', '사용자')
        
        if 5 <= hour < 12:
            greeting = f"{user_name}님, 좋은 아침입니다"
            time_icon = "🌅"
            bg_image_name = "bg_morning.png"
        elif 12 <= hour < 17:
            greeting = f"{user_name}님, 좋은 오후입니다"
            time_icon = "☀️"
            bg_image_name = "bg_afternoon.png"
        else:
            greeting = f"{user_name}님, 좋은 저녁입니다"
            time_icon = "🌙"
            bg_image_name = "bg_night.png"
            
        bg_path = os.path.join(ASSETS_DIR, "images", bg_image_name).replace('\\', '/')
        
        self.view = HomeViewWidget(bg_path, self)
        self.view.setObjectName("HomeView")
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        
        self.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            #HomeInterface { background: transparent; }
        """)
        
        self.overlay = QFrame()
        self.overlay.setStyleSheet("background-color: rgba(10, 10, 15, 0.65);")
        
        self.base_layout = QVBoxLayout(self.view)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.base_layout.addWidget(self.overlay)
        
        self.main_vbox = QVBoxLayout(self.overlay)
        self.main_vbox.setContentsMargins(60, 60, 60, 60)
        self.main_vbox.setSpacing(50)
        
        # HEADER
        self.header_layout = QHBoxLayout()
        
        self.header_left_layout = QHBoxLayout()
        self.header_left_layout.setSpacing(20)
        
        self.icon_label = QLabel(time_icon)
        self.icon_label.setFont(QFont("Segoe UI Emoji", 48))
        self.icon_label.setStyleSheet("background: transparent;")
        
        self.greeting_vbox = QVBoxLayout()
        self.greeting_label = QLabel(greeting)
        self.greeting_label.setFont(QFont("SUIT", 42, QFont.Bold))
        self.greeting_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        
        self.subtitle_label = QLabel("푸름애드 관리 프로그램에 오신 것을 환영합니다.")
        self.subtitle_label.setFont(QFont("SUIT", 16))
        self.subtitle_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        
        self.greeting_vbox.addWidget(self.greeting_label)
        self.greeting_vbox.addWidget(self.subtitle_label)
        
        self.header_left_layout.addWidget(self.icon_label)
        self.header_left_layout.addLayout(self.greeting_vbox)
        
        self.version_label = QLabel(f"Program ver : {VERSION}")
        self.version_label.setFont(QFont("SUIT", 12))
        self.version_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); background: transparent;")
        self.version_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        
        self.header_layout.addLayout(self.header_left_layout)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.version_label)
        
        self.main_vbox.addLayout(self.header_layout)
        
        # BODY
        self.body_layout = QHBoxLayout()
        self.body_layout.setSpacing(60)
        
        # Left Panel (Features)
        self.left_panel = QVBoxLayout()
        self.left_panel.setSpacing(20)
        self.feature_title = QLabel("빠른 실행")
        self.feature_title.setFont(QFont("SUIT", 18, QFont.Bold))
        self.feature_title.setStyleSheet("color: rgba(255, 255, 255, 0.9); background: transparent;")
        self.left_panel.addWidget(self.feature_title)
        
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(20)
        
        self.scraper_card = FeatureCard(FluentIcon.DOCUMENT, "블로그 순위 체크", "키워드별 블로그 순위 탐색")
        self.place_card = FeatureCard(getattr(FluentIcon, "POI", FluentIcon.SEARCH), "플레이스 순위 체크", "키워드별 플레이스 순위 탐색")
        self.index_card = FeatureCard(getattr(FluentIcon, "PIE_SINGLE", FluentIcon.DOCUMENT), "블로그 통계 대시보드", "블로그 지수 분석 및 확인")
        self.holiday_card = FeatureCard(getattr(FluentIcon, "CHECKBOX", FluentIcon.ACCEPT), "업체별 휴진 체크", "업체별 휴진 정보 체크 및 동기화")
        self.company_card = FeatureCard(FluentIcon.PEOPLE, "업체 리스트", "업체별 링크 관리, 휴진 체크")
        
        self.schedule_card = MonthlyScheduleSummaryCard(self.main_window)
        
        # Start fetching today's schedule
        from datetime import date
        self.fetch_thread = ScheduleFetchThread()
        self.fetch_thread.data_fetched.connect(self.on_schedule_fetched)
        self.fetch_thread.start()
        
        self.scraper_card.clicked.connect(lambda: self.main_window.switchTo(self.main_window.scraper_interface))
        self.place_card.clicked.connect(lambda: self.main_window.switchTo(self.main_window.place_scraper_interface))
        self.index_card.clicked.connect(lambda: self.main_window.switchTo(self.main_window.index_check_interface))
        self.holiday_card.clicked.connect(lambda: self.main_window.switchTo(self.main_window.holiday_check_interface))
        self.company_card.clicked.connect(lambda: self.main_window.switchTo(self.main_window.company_list_interface))
        
        self.grid_layout.addWidget(self.scraper_card, 0, 0)
        self.grid_layout.addWidget(self.place_card, 0, 1)
        self.grid_layout.addWidget(self.index_card, 1, 0)
        self.grid_layout.addWidget(self.holiday_card, 1, 1)
        self.grid_layout.addWidget(self.company_card, 2, 0)
        self.grid_layout.addWidget(self.schedule_card, 2, 1)
        
        self.left_panel.addLayout(self.grid_layout)
        self.left_panel.addStretch(1)
        
        # Right Panel (News)
        self.right_panel = QVBoxLayout()
        self.right_panel.setSpacing(20)
        self.news_title = QLabel("마케팅 주요 뉴스")
        self.news_title.setFont(QFont("SUIT", 18, QFont.Bold))
        self.news_title.setStyleSheet("color: rgba(255, 255, 255, 0.9); background: transparent;")
        self.right_panel.addWidget(self.news_title)
        
        self.news_container = QFrame()
        self.news_container.setObjectName("NewsContainer")
        self.news_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.news_container.setStyleSheet("""
            #NewsContainer {
                background-color: rgba(30, 30, 35, 0.85);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
        """)
        self.news_layout = QVBoxLayout(self.news_container)
        self.news_layout.setContentsMargins(30, 30, 30, 30)
        self.news_layout.setSpacing(16)
        
        self.loading_label = QLabel("뉴스를 불러오는 중입니다...")
        self.loading_label.setFont(QFont("SUIT", 11))
        self.loading_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); background: transparent;")
        self.news_layout.addWidget(self.loading_label)
        self.news_layout.addStretch(1)
        
        self.right_panel.addWidget(self.news_container)
        
        self.body_layout.addLayout(self.left_panel, 5)
        self.body_layout.addLayout(self.right_panel, 5)
        
        self.main_vbox.addLayout(self.body_layout)
        self.main_vbox.addStretch(1)
        
        # Fetch News
        self.worker = NewsWorker()
        self.worker.finished.connect(self.on_news_fetched)
        self.worker.error.connect(self.on_news_error)
        self.worker.start()
        
    def on_news_fetched(self, news_items):
        self.loading_label.hide()
        for i in reversed(range(self.news_layout.count())): 
            widget = self.news_layout.itemAt(i).widget()
            if widget is not None and widget != self.loading_label:
                widget.deleteLater()
                
        for item in news_items:
            link = HyperlinkButton(item['url'], item['title'])
            link.setFont(QFont("SUIT", 11))
            link.setStyleSheet("""
                HyperlinkButton {
                    color: #60CDFF;
                    background: transparent;
                    border: none;
                    text-align: left;
                    padding: 4px;
                }
                HyperlinkButton:hover {
                    color: #A6D8FF;
                    background-color: rgba(255, 255, 255, 0.05);
                    border-radius: 6px;
                }
            """)
            self.news_layout.insertWidget(self.news_layout.count() - 1, link)
            
    def on_news_error(self, err):
        self.loading_label.setText(f"뉴스를 불러오는데 실패했습니다: {err}")

    def on_schedule_fetched(self, data):
        schedules = data.get('schedules', [])
        from datetime import date
        today_str = str(date.today())
        today_schedules = []
        for row in schedules:
            if len(row) >= 3 and row[0].strip() == today_str:
                # row is [date, text, color, creator_id]
                today_schedules.append((row[1].strip(), row[2]))
        
        holidays = data.get('holidays', {})
        holiday_today = holidays.get(today_str)
        if holiday_today:
            today_schedules.insert(0, (f"공휴일: {holiday_today}", "#ff6b6b"))
            
        self.schedule_card.update_schedule(today_schedules)

