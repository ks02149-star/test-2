
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
from src.ui.components.cards import PlaceExposureCard, FavoritePlaceCard
from src.ui.components.dialogs import FavoriteEditDialog
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, FONT_DIR, SETTINGS_PATH, CREDENTIALS_PATH

class PlaceScraperInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("PlaceScraperInterface")
        self.global_driver_path = ""
        self.favorites_data = []
        self.favorite_cards = []
        self.task_queue = []
        self.current_task = None
        
        self.load_favorites()
        self.init_ui()
        self.check_environment()
        
    def load_favorites(self):
        self.favorites_path = os.path.join(DATA_DIR, "place_favorites.json")
        if os.path.exists(self.favorites_path):
            try:
                with open(self.favorites_path, 'r', encoding='utf-8') as f:
                    self.favorites_data = json.load(f)
            except Exception:
                self.favorites_data = [{} for _ in range(12)]
        else:
            self.favorites_data = [{} for _ in range(12)]
            
        while len(self.favorites_data) < 12:
            self.favorites_data.append({})
            
    def save_favorites(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        try:
            with open(self.favorites_path, 'w', encoding='utf-8') as f:
                json.dump(self.favorites_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Failed to save favorites: {e}")

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
        
        self.record_switch = SwitchButton(self)
        self.record_switch.setOnText("기록 모드 ON")
        self.record_switch.setOffText("기록 모드 OFF")
        button_layout.addWidget(self.record_switch)
        
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
        
        fav_title = SubtitleLabel("즐겨찾기")
        fav_title.setFont(QFont("SUIT", 12, QFont.Bold))
        right_layout.addWidget(fav_title)
        
        self.fav_grid = QGridLayout()
        self.fav_grid.setSpacing(8)
        
        for i in range(12):
            card = FavoritePlaceCard(i, self.favorites_data[i], self)
            card.double_clicked.connect(self.edit_favorite)
            card.single_clicked.connect(self.queue_favorite_task)
            card.cancel_clicked.connect(self.cancel_favorite_task)
            row = i // 4
            col = i % 4
            self.fav_grid.addWidget(card, row, col)
            self.favorite_cards.append(card)
            
        right_layout.addLayout(self.fav_grid)
        
        right_layout.addSpacing(16)
        
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

    def edit_favorite(self, index):
        dialog = FavoriteEditDialog(self.favorites_data[index], self)
        if dialog.exec_():
            data = dialog.get_data()
            self.favorites_data[index] = data
            self.save_favorites()
            self.favorite_cards[index].update_data(data)

    def queue_favorite_task(self, index):
        data = self.favorites_data[index]
        keyword = data.get('keyword', '')
        company = data.get('company', '')
        count = data.get('count', 50)
        
        if not keyword or not company:
            InfoBar.warning("입력 필요", "키워드와 업체명을 모두 설정해주세요.", duration=3000, parent=self)
            return
            
        task = {
            'type': 'favorite',
            'index': index,
            'keyword': keyword,
            'company': company,
            'count': count,
            'record_mode': self.record_switch.isChecked()
        }
        self.task_queue.append(task)
        self.favorite_cards[index].set_status("queued")
        self.append_log(f"[대기열 추가] 즐겨찾기 {index+1}번: '{keyword}' / '{company}'")
        self.start_btn.setEnabled(False)
        self.process_next_task()

    def cancel_favorite_task(self, index):
        card = self.favorite_cards[index]
        if card.status == "queued":
            self.task_queue = [t for t in self.task_queue if not (t.get('type') == 'favorite' and t.get('index') == index)]
            card.set_status("idle")
            self.append_log(f"[취소] 즐겨찾기 {index+1}번 대기열에서 제거됨.")
            if not self.task_queue and not (hasattr(self, 'worker') and self.worker and self.worker.isRunning()):
                self.start_btn.setEnabled(True)
        elif card.status == "running":
            if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
                self.worker.stop()
                self.append_log(f"[취소] 즐겨찾기 {index+1}번 작업 취소 요청 중...")

    def start_scraping(self):
        keyword = self.keyword_input.text().strip()
        company = self.company_input.text().strip()
        
        if not keyword or not company:
            InfoBar.error("입력 오류", "검색 키워드와 목표 업체명을 모두 입력해주세요.", duration=3000, position=InfoBarPosition.TOP, parent=self)
            return

        display_count = self.count_spinbox.value()
        
        task = {
            'type': 'manual',
            'keyword': keyword,
            'company': company,
            'count': display_count,
            'record_mode': self.record_switch.isChecked()
        }
        self.task_queue.append(task)
        self.append_log(f"[대기열 추가] 수동 검색: '{keyword}' / '{company}'")
        self.start_btn.setEnabled(False)
        self.process_next_task()

    def process_next_task(self):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            return
            
        if not self.task_queue:
            self.start_btn.setEnabled(True)
            self.append_log("\n[안내] 모든 대기열 작업이 종료되었습니다.")
            InfoBar.success("완료", "모든 순위 체크 작업이 종료되었습니다.", duration=4000, position=InfoBarPosition.TOP, parent=self)
            return
            
        self.current_task = self.task_queue.pop(0)
        
        self.keyword_input.setEnabled(False)
        self.company_input.setEnabled(False)
        self.count_spinbox.setEnabled(False)
        self.start_btn.setEnabled(False)
        
        if self.current_task['type'] == 'favorite':
            self.favorite_cards[self.current_task['index']].set_status("running")
            
        self.worker = PlaceScraperWorker(
            self.current_task['keyword'], 
            self.current_task['company'], 
            self.current_task['count'], 
            self.global_driver_path,
            self.current_task.get('record_mode', False)
        )
        self.worker.signals.log.connect(self.append_log)
        self.worker.signals.error.connect(self.show_error)
        self.worker.signals.match_found.connect(self.on_match_found)
        self.worker.signals.finished.connect(self.on_scraping_finished)
        self.worker.start()

    def on_match_found(self, match_data):
        self.add_exposure_card(match_data)
        if self.current_task and self.current_task['type'] == 'favorite':
            self.current_task['ranks'] = match_data.get('ranks', [])

    def show_error(self, err_msg):
        if "사용자에 의해 취소" in err_msg:
            self.on_scraping_finished(has_error=True)
            return
            
        InfoBar.error("작업 중단", err_msg, duration=5000, position=InfoBarPosition.TOP, parent=self)
        self.on_scraping_finished(has_error=True)

    def on_scraping_finished(self, has_error=False):
        if self.current_task and self.current_task['type'] == 'favorite':
            ranks = self.current_task.get('ranks', [])
            if has_error:
                self.favorite_cards[self.current_task['index']].set_status("idle")
            else:
                self.favorite_cards[self.current_task['index']].set_status("done", ranks)
                
        if hasattr(self, 'worker') and self.worker:
            self.worker.deleteLater()
            self.worker = None
            
        self.current_task = None
        self.keyword_input.setEnabled(True)
        self.company_input.setEnabled(True)
        self.count_spinbox.setEnabled(True)
        
        self.process_next_task()
