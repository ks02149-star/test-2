import re

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
from src.core.scraper_threads import SpellCheckWorker
from src.ui.components.cards import SpellCheckIssueCard
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, FONT_DIR, SETTINGS_PATH, CREDENTIALS_PATH

class SpellCheckInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SpellCheckInterface")
        self.worker = None
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 22, 36, 22)
        main_layout.setSpacing(20)
        
        # Title
        title_layout = QHBoxLayout()
        title_lbl = TitleLabel("맞춤법 검사기", self)
        title_layout.addWidget(title_lbl)
        
        self.status_lbl = QLabel("", self)
        self.status_lbl.setFont(QFont("SUIT", 11))
        self.status_lbl.setStyleSheet("color: #A0A0A0; background: transparent; border: none;")
        title_layout.addWidget(self.status_lbl)
        
        title_layout.addStretch(1)
        
        self.progress_ring = IndeterminateProgressRing(self)
        self.progress_ring.setFixedSize(20, 20)
        self.progress_ring.hide()
        title_layout.addWidget(self.progress_ring)
        
        main_layout.addLayout(title_layout)
        
        # Split layout (Left: Input, Right: Output)
        split_layout = QHBoxLayout()
        split_layout.setSpacing(24)
        
        # Left Panel (Input)
        left_panel = QWidget(self)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        
        left_layout.addWidget(SubtitleLabel("검사할 텍스트"))
        
        self.input_edit = TextEdit(self)
        self.input_edit.setPlaceholderText("여기에 검사할 텍스트를 입력하거나 붙여넣으세요...")
        self.input_edit.setFont(QFont("SUIT", 12))
        left_layout.addWidget(self.input_edit)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.check_btn = PrimaryPushButton("검사 시작", self)
        self.check_btn.setFixedWidth(120)
        self.check_btn.clicked.connect(self.start_check)
        
        self.clear_btn = PushButton("비우기", self)
        self.clear_btn.setFixedWidth(100)
        self.clear_btn.clicked.connect(self.clear_text)
        
        btn_layout.addWidget(self.check_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch(1)
        left_layout.addLayout(btn_layout)
        
        split_layout.addWidget(left_panel, 3)
        
        # Right Panel (Output & Details)
        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        
        right_layout.addWidget(SubtitleLabel("교정 완료 결과"))
        
        self.output_edit = TextEdit(self)
        self.output_edit.setReadOnly(True)
        self.output_edit.setFont(QFont("SUIT", 12))
        right_layout.addWidget(self.output_edit, 2)
        
        right_layout.addWidget(SubtitleLabel("상세 교정 내역"))
        
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_content.setStyleSheet("QWidget#ScrollContent { background: transparent; }")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 10, 0)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch(1)
        
        self.scroll_area.setWidget(self.scroll_content)
        right_layout.addWidget(self.scroll_area, 3)
        
        split_layout.addWidget(right_panel, 2)
        
        main_layout.addLayout(split_layout)
        
        self.update_style()
        qconfig.themeChanged.connect(self.update_style)
        
    def update_style(self):
        is_dark = isDarkTheme()
        bg_color = "#202020" if is_dark else "#FFFFFF"
        border_color = "#3A3A3A" if is_dark else "#E5E5E5"
        self.scroll_area.setStyleSheet(f"QScrollArea {{ border: 1px solid {border_color}; border-radius: 8px; background-color: {bg_color}; }}")
        
    def clear_text(self):
        self.input_edit.clear()
        self.output_edit.clear()
        self.clear_cards()
        self.status_lbl.setText("")
        
    def clear_cards(self):
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.scroll_layout.addStretch(1)
        
    def start_check(self):
        text = self.input_edit.toPlainText().strip()
        if not text:
            InfoBar.warning("안내", "검사할 텍스트를 입력해주세요.", duration=3000, parent=self)
            return
            
        self.check_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.progress_ring.show()
        self.progress_ring.start()
        self.status_lbl.setText("맞춤법 검사 중...")
        self.output_edit.clear()
        self.clear_cards()
        
        self.worker = SpellCheckWorker(text, self)
        self.worker.finished.connect(self.on_check_finished)
        self.worker.error.connect(self.on_check_error)
        self.worker.start()
        
    def on_check_finished(self, result):
        self.check_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.progress_ring.stop()
        self.progress_ring.hide()
        self.status_lbl.setText("검사 완료")
        
        corrected_text = result.get("corrected_text", "")
        issues = result.get("issues", [])
        
        rendered_html = corrected_text.replace("\n", "<br>")
        
        unique_suggestions = sorted(list(set(issue.suggestions[0] for issue in issues if issue.suggestions)), key=len, reverse=True)
        for sug in unique_suggestions:
            if sug:
                highlight_tag = f'<span style="background-color: rgba(10, 132, 255, 0.28); color: #60CDFF; font-weight: 800; border-radius: 4px; padding: 2px 4px;">{sug}</span>'
                escaped_sug = re.escape(sug)
                rendered_html = re.sub(rf'(?<![0-9a-zA-Z가-힣]){escaped_sug}(?![0-9a-zA-Z가-힣])(?![^<]*>)', highlight_tag, rendered_html)
                
        self.output_edit.setHtml(f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: 'SUIT', sans-serif;
                        font-size: 16px;
                        color: #E5E5E5;
                        line-height: 1.8;
                    }}
                </style>
            </head>
            <body>
                {rendered_html}
            </body>
            </html>
        """)
        
        if issues:
            for issue in issues:
                card = SpellCheckIssueCard(issue, self.scroll_content)
                insert_idx = max(0, self.scroll_layout.count() - 1)
                self.scroll_layout.insertWidget(insert_idx, card)
        else:
            no_issue_lbl = QLabel("검출된 맞춤법 오류가 없습니다. 완벽한 문장입니다!", self.scroll_content)
            no_issue_lbl.setFont(QFont("SUIT", 12, QFont.Bold))
            no_issue_lbl.setAlignment(Qt.AlignCenter)
            no_issue_lbl.setStyleSheet("color: #40C463; padding: 20px; background: transparent; border: none;")
            insert_idx = max(0, self.scroll_layout.count() - 1)
            self.scroll_layout.insertWidget(insert_idx, no_issue_lbl)
            
    def on_check_error(self, err_msg):
        self.check_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.progress_ring.stop()
        self.progress_ring.hide()
        self.status_lbl.setText("오류 발생")
        
        MessageBox("맞춤법 검사 실패", f"맞춤법 검사 중 오류가 발생했습니다:\n{err_msg}", self).exec_()

