
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
from src.core.scraper_threads import DriverInitWorker, PlaceScraperWorker
from src.ui.components.cards import PlaceExposureCard
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, FONT_DIR, SETTINGS_PATH, CREDENTIALS_PATH

class PlaceScraperInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("PlaceScraperInterface")
        self.global_driver_path = ""
        
        self.init_ui()
        self.check_environment()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 36, 36, 36)
        main_layout.setSpacing(16)

        self.title_label = TitleLabel("플레이스 순위 체크")
        main_layout.addWidget(self.title_label)

        split_layout = QHBoxLayout()
        split_layout.setSpacing(24)
        
        self.left_panel = QWidget(self)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        input_layout = QGridLayout()
        input_layout.setSpacing(12)
        
        self.keyword_input = LineEdit()
        self.keyword_input.setPlaceholderText("예: 부산 성형외과")
        input_layout.addWidget(SubtitleLabel("검색 키워드:"), 0, 0)
        input_layout.addWidget(self.keyword_input, 0, 1)
        
        self.company_input = LineEdit()
        self.company_input.setPlaceholderText("예: 푸름애드 의원")
        input_layout.addWidget(SubtitleLabel("목표 업체명:"), 1, 0)
        input_layout.addWidget(self.company_input, 1, 1)
        
        self.count_spinbox = SpinBox()
        self.count_spinbox.setRange(1, 150)
        self.count_spinbox.setValue(50)
        input_layout.addWidget(SubtitleLabel("탐색 목표 개수:"), 2, 0)
        input_layout.addWidget(self.count_spinbox, 2, 1)
        
        left_layout.addLayout(input_layout)

        self.loading_container = QWidget()
        loading_layout = QHBoxLayout(self.loading_container)
        loading_layout.setAlignment(Qt.AlignCenter)
        loading_layout.setContentsMargins(0, 0, 0, 0)
        
        self.loading_ring = IndeterminateProgressRing()
        self.loading_ring.setFixedSize(25, 25)
        self.loading_label = SubtitleLabel("크롬 드라이버를 점검/동기화 중입니다...")
        
        loading_layout.addWidget(self.loading_ring)
        loading_layout.addWidget(self.loading_label)
        left_layout.addWidget(self.loading_container)
        self.loading_container.hide()

        button_layout = QHBoxLayout()
        
        self.start_btn = PushButton("순위 체크 시작")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #3CA0F0;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-family: 'SUIT';
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #59B4FF;
            }
            QPushButton:pressed {
                background-color: #268CD9;
            }
            QPushButton:disabled {
                background-color: #2C2C2C;
                color: #666666;
            }
        """)
        self.start_btn.clicked.connect(self.start_scraping)
        button_layout.addWidget(self.start_btn)
        button_layout.addStretch(1)
        
        left_layout.addLayout(button_layout)

        self.console_output = TextEdit()
        self.console_output.setReadOnly(True)
        left_layout.addWidget(self.console_output)

        split_layout.addWidget(self.left_panel, 3) 

        self.right_panel = QWidget(self)
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        
        right_title = SubtitleLabel("실시간 노출 현황")
        right_title.setFont(QFont("SUIT", 12, QFont.Bold))
        right_layout.addWidget(right_title)
        
        self.exposure_scroll = ScrollArea(self.right_panel)
        self.exposure_scroll.setWidgetResizable(True)
        
        self.exposure_content = QWidget()
        self.exposure_content.setObjectName("ExposureContent")
        self.exposure_content.setStyleSheet("QWidget#ExposureContent { background-color: transparent; }")
        self.exposure_layout = QVBoxLayout(self.exposure_content)
        self.exposure_layout.setContentsMargins(12, 12, 12, 12)
        self.exposure_layout.setSpacing(12)
        self.exposure_layout.addStretch(1)
        
        self.exposure_scroll.setWidget(self.exposure_content)
        right_layout.addWidget(self.exposure_scroll)
        
        split_layout.addWidget(self.right_panel, 2) 

        main_layout.addLayout(split_layout)

        self.update_right_panel_style()
        qconfig.themeChanged.connect(self.update_right_panel_style)

    def update_right_panel_style(self):
        is_dark = isDarkTheme()
        border_color = "#3A3A3A" if is_dark else "#E5E5E5"
        bg_color = "#202020" if is_dark else "#FFFFFF"
        self.exposure_scroll.setStyleSheet(f"QScrollArea {{ border: 1px solid {border_color}; border-radius: 8px; background-color: {bg_color}; }}")

    def clear_exposure_cards(self):
        while self.exposure_layout.count():
            child = self.exposure_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.exposure_layout.addStretch(1)

    def add_exposure_card(self, match_data):
        card = PlaceExposureCard(match_data, self.exposure_content)
        self.exposure_layout.insertWidget(0, card)
        
        while self.exposure_layout.count() > 7:
            idx_to_remove = self.exposure_layout.count() - 2
            item = self.exposure_layout.takeAt(idx_to_remove)
            if item.widget():
                item.widget().deleteLater()

    def append_log(self, text):
        self.console_output.append(text)
        scrollbar = self.console_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def check_environment(self):
        self.append_log("[시스템] 초기 환경을 점검합니다...")
        self.start_btn.setEnabled(False)
        self.loading_container.show()
        self.loading_ring.start()
        
        self.driver_worker = DriverInitWorker()
        self.driver_worker.finished.connect(self.on_driver_ready)
        self.driver_worker.error.connect(self.on_driver_error)
        self.driver_worker.start()

    def on_driver_ready(self, path):
        self.global_driver_path = path
        self.loading_ring.stop()
        self.loading_container.hide()
        self.append_log("[시스템] 크롬 드라이버 동기화 및 준비 완료.")
        self.start_btn.setEnabled(True)

    def on_driver_error(self, err_msg):
        self.loading_ring.stop()
        self.loading_container.hide()
        self.append_log(f"[치명적 오류] 크롬 드라이버 설치 실패: {err_msg}")
        InfoBar.error("오류", "크롬 드라이버를 설치할 수 없습니다.", duration=5000, position=InfoBarPosition.TOP, parent=self)

    def start_scraping(self):
        keyword = self.keyword_input.text()
        company = self.company_input.text()
        
        if not keyword.strip() or not company.strip():
            InfoBar.error("입력 오류", "검색 키워드와 목표 업체명을 모두 입력해주세요.", duration=3000, position=InfoBarPosition.TOP, parent=self)
            return

        self.start_btn.setEnabled(False)
        self.keyword_input.setEnabled(False)
        self.company_input.setEnabled(False)
        self.count_spinbox.setEnabled(False)
        self.console_output.clear()
        
        display_count = self.count_spinbox.value()

        self.worker = PlaceScraperWorker(
            keyword, company, display_count, self.global_driver_path
        )
        self.worker.signals.log.connect(self.append_log)
        self.worker.signals.error.connect(self.show_error)
        self.worker.signals.match_found.connect(self.add_exposure_card)
        self.worker.signals.finished.connect(self.on_scraping_finished)
        self.worker.start()

    def show_error(self, err_msg):
        InfoBar.error("작업 중단", err_msg, duration=5000, position=InfoBarPosition.TOP, parent=self)
        self.on_scraping_finished()

    def on_scraping_finished(self):
        self.start_btn.setEnabled(True)
        self.keyword_input.setEnabled(True)
        self.company_input.setEnabled(True)
        self.count_spinbox.setEnabled(True)
        self.append_log("\n[안내] 순위 체크가 종료되었습니다.")
        InfoBar.success("완료", "플레이스 순위 체크 작업이 성공적으로 종료되었습니다.", duration=4000, position=InfoBarPosition.TOP, parent=self)

