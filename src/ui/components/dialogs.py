from src.utils.helpers import load_companies, save_companies

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

class CompanyDialog(QDialog):
    def __init__(self, company_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("업체 정보 입력")
        self.setFixedSize(450, 580)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(14)
        
        title_text = "업체 정보 수정" if company_data else "새 업체 추가"
        self.title_label = SubtitleLabel(title_text, self)
        self.layout.addWidget(self.title_label)
        
        # Form Fields
        self.inputs = {}
        self.labels = []
        fields = [
            ('name', '업체명 *'),
            ('homepage', '홈페이지 주소'),
            ('place', '플레이스 주소'),
            ('blog_id', '네이버 블로그 ID'),
            ('blog1', '블로그 1 주소'),
            ('blog2', '블로그 2 주소'),
            ('instagram', '인스타그램 주소')
        ]
        
        for key, label in fields:
            row_layout = QVBoxLayout()
            row_layout.setSpacing(4)
            
            lbl = QLabel(label, self)
            lbl.setFont(QFont("SUIT", 10, QFont.Bold))
            row_layout.addWidget(lbl)
            self.labels.append((lbl, key == 'name'))
            
            edit = LineEdit(self)
            edit.setPlaceholderText(f"{label} 입력")
            if company_data:
                edit.setText(company_data.get(key, ''))
                
            row_layout.addWidget(edit)
            self.layout.addLayout(row_layout)
            self.inputs[key] = edit
            
        self.layout.addStretch(1)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch(1)
        
        self.ok_btn = PushButton("저장", self)
        self.ok_btn.clicked.connect(self.validate_and_accept)
        
        self.cancel_btn = PushButton("취소", self)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        self.layout.addLayout(btn_layout)
        
        self.update_style()
        qconfig.themeChanged.connect(self.update_style)
        
    def update_style(self):
        is_dark = isDarkTheme()
        bg_color = "#202020" if is_dark else "#FFFFFF"
        text_color = "#FFFFFF" if is_dark else "#000000"
        label_color = "#AAAAAA" if is_dark else "#333333"
        required_color = "#FF6B6B" if is_dark else "#D83B01"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
        """)
        
        self.title_label.setStyleSheet(f"color: {text_color}; background: transparent;")
        
        for lbl, is_required in self.labels:
            color = required_color if is_required else label_color
            lbl.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold; background: transparent;")
            
        # Style text inputs to make sure they are highly readable
        input_bg = "#161616" if is_dark else "#FFFFFF"
        input_fg = "#FFFFFF" if is_dark else "#000000"
        input_border = "#3A3A3A" if is_dark else "#CCCCCC"
        
        for edit in self.inputs.values():
            edit.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {input_bg};
                    color: {input_fg};
                    border: 1px solid {input_border};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-family: 'SUIT';
                }}
                QLineEdit:focus {{
                    border: 1px solid #0078D4;
                }}
            """)
            
        # Action Buttons Style
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
                font-family: 'SUIT';
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
        """)
        
        cancel_bg = "#1E1E1E" if is_dark else "#F3F3F3"
        cancel_fg = "#FFFFFF" if is_dark else "#000000"
        cancel_border = "#3A3A3A" if is_dark else "#CCCCCC"
        cancel_hover = "#2C2C2C" if is_dark else "#EBEBEB"
        
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {cancel_bg};
                color: {cancel_fg};
                border: 1px solid {cancel_border};
                border-radius: 4px;
                padding: 6px 16px;
                font-family: 'SUIT';
            }}
            QPushButton:hover {{
                background-color: {cancel_hover};
            }}
        """)
        
    def validate_and_accept(self):
        name = self.inputs['name'].text().strip()
        if not name:
            QMessageBox.warning(self, "입력 오류", "업체명은 필수 입력 항목입니다.")
            return
        self.accept()
        
    def get_data(self):
        return {
            'name': self.inputs['name'].text().strip(),
            'homepage': self.inputs['homepage'].text().strip(),
            'place': self.inputs['place'].text().strip(),
            'blog_id': self.inputs['blog_id'].text().strip(),
            'blog1': self.inputs['blog1'].text().strip(),
            'blog2': self.inputs['blog2'].text().strip(),
            'instagram': self.inputs['instagram'].text().strip()
        }

    def closeEvent(self, event):
        try:
            qconfig.themeChanged.disconnect(self.update_style)
        except Exception:
            pass
        super().closeEvent(event)
from src.utils.helpers import load_companies, save_companies

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

class CompanyDialog(QDialog):
    def __init__(self, company_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("업체 정보 입력")
        self.setFixedSize(450, 700)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(14)
        
        title_text = "업체 정보 수정" if company_data else "새 업체 추가"
        self.title_label = SubtitleLabel(title_text, self)
        self.layout.addWidget(self.title_label)
        
        # Form Fields
        self.inputs = {}
        self.labels = []
        fields = [
            ('name', '업체명 *'),
            ('homepage', '홈페이지 주소'),
            ('place', '플레이스 주소'),
            ('blog_id', '네이버 블로그 ID'),
            ('blog1', '블로그 1 주소'),
            ('blog2', '블로그 2 주소'),
            ('instagram', '인스타그램 주소')
        ]
        
        for key, label in fields:
            row_layout = QVBoxLayout()
            row_layout.setSpacing(4)
            
            lbl = QLabel(label, self)
            lbl.setFont(QFont("SUIT", 10, QFont.Bold))
            row_layout.addWidget(lbl)
            self.labels.append((lbl, key == 'name'))
            
            edit = LineEdit(self)
                
            edit.setPlaceholderText(f"{label} 입력")
            if company_data:
                edit.setText(company_data.get(key, ''))
                
            row_layout.addWidget(edit)
            self.layout.addLayout(row_layout)
            self.inputs[key] = edit
            
        self.layout.addStretch(1)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch(1)
        
        self.ok_btn = PushButton("저장", self)
        self.ok_btn.clicked.connect(self.validate_and_accept)
        
        self.cancel_btn = PushButton("취소", self)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        self.layout.addLayout(btn_layout)
        
        self.update_style()
        qconfig.themeChanged.connect(self.update_style)
        
    def update_style(self):
        is_dark = isDarkTheme()
        bg_color = "#202020" if is_dark else "#FFFFFF"
        text_color = "#FFFFFF" if is_dark else "#000000"
        label_color = "#AAAAAA" if is_dark else "#333333"
        required_color = "#FF6B6B" if is_dark else "#D83B01"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
        """)
        
        self.title_label.setStyleSheet(f"color: {text_color}; background: transparent;")
        
        for lbl, is_required in self.labels:
            color = required_color if is_required else label_color
            lbl.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold; background: transparent;")
            
        # Style text inputs to make sure they are highly readable
        input_bg = "#161616" if is_dark else "#FFFFFF"
        input_fg = "#FFFFFF" if is_dark else "#000000"
        input_border = "#3A3A3A" if is_dark else "#CCCCCC"
        
        for edit in self.inputs.values():
            edit.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {input_bg};
                    color: {input_fg};
                    border: 1px solid {input_border};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-family: 'SUIT';
                }}
                QLineEdit:focus {{
                    border: 1px solid #0078D4;
                }}
            """)
            
        # Action Buttons Style
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
                font-family: 'SUIT';
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
        """)
        
        cancel_bg = "#1E1E1E" if is_dark else "#F3F3F3"
        cancel_fg = "#FFFFFF" if is_dark else "#000000"
        cancel_border = "#3A3A3A" if is_dark else "#CCCCCC"
        cancel_hover = "#2C2C2C" if is_dark else "#EBEBEB"
        
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {cancel_bg};
                color: {cancel_fg};
                border: 1px solid {cancel_border};
                border-radius: 4px;
                padding: 6px 16px;
                font-family: 'SUIT';
            }}
            QPushButton:hover {{
                background-color: {cancel_hover};
            }}
        """)
        
    def validate_and_accept(self):
        name = self.inputs['name'].text().strip()
        if not name:
            QMessageBox.warning(self, "입력 오류", "업체명은 필수 입력 항목입니다.")
            return
        self.accept()
        
    def get_data(self):
        return {
            'name': self.inputs['name'].text().strip(),
            'homepage': self.inputs['homepage'].text().strip(),
            'place': self.inputs['place'].text().strip(),
            'blog_id': self.inputs['blog_id'].text().strip(),
            'blog1': self.inputs['blog1'].text().strip(),
            'blog2': self.inputs['blog2'].text().strip(),
            'instagram': self.inputs['instagram'].text().strip()
        }

    def closeEvent(self, event):
        try:
            qconfig.themeChanged.disconnect(self.update_style)
        except Exception:
            pass
        super().closeEvent(event)


class ScheduleAddDialog(QDialog):
    def __init__(self, date_str, parent=None):
        super().__init__(parent)
        self.date_str = date_str
        self.setWindowTitle(f"일정 추가 - {date_str}")
        self.setFixedSize(480, 310)
        
        from qfluentwidgets import isDarkTheme, CalendarPicker, qconfig
        from PyQt5.QtCore import QDate
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(16)
        
        self.title_label = SubtitleLabel("새로운 일정", self)
        self.layout.addWidget(self.title_label)
        
        # 날짜 선택 영역
        date_layout = QHBoxLayout()
        date_layout.setSpacing(12)
        
        self.start_picker = CalendarPicker()
        self.end_picker = CalendarPicker()
        
        y, m, d = map(int, date_str.split('-'))
        initial_date = QDate(y, m, d)
        self.start_picker.setDate(initial_date)
        self.end_picker.setDate(initial_date)
        
        start_lbl = BodyLabel("시작 일자")
        end_lbl = BodyLabel("종료 일자")
        
        date_layout.addWidget(start_lbl)
        date_layout.addWidget(self.start_picker)
        date_layout.addStretch(1)
        date_layout.addWidget(end_lbl)
        date_layout.addWidget(self.end_picker)
        
        self.layout.addLayout(date_layout)
        
        # 일정 제목 입력
        self.input_edit = LineEdit()
        self.input_edit.setPlaceholderText("일정 제목을 입력하세요 (예: OOO 미팅)")
        self.input_edit.setClearButtonEnabled(True)
        self.layout.addWidget(self.input_edit)
        
        # 체크박스 (유형 선택)
        check_layout = QHBoxLayout()
        check_layout.setSpacing(12)
        self.chk_meeting = CheckBox("미팅")
        self.chk_work = CheckBox("작업")
        self.chk_annual = CheckBox("연차")
        self.chk_am_half = CheckBox("오전반차")
        self.chk_pm_half = CheckBox("오후반차")
        
        self.checkboxes = [self.chk_meeting, self.chk_work, self.chk_annual, self.chk_am_half, self.chk_pm_half]
        for chk in self.checkboxes:
            check_layout.addWidget(chk)
            chk.stateChanged.connect(self.on_checkbox_changed)
            
        check_layout.addStretch(1)
        self.layout.addLayout(check_layout)
        
        self.layout.addStretch(1)
        
        # 버튼 영역
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch(1)
        
        self.save_btn = PrimaryPushButton("저장")
        self.save_btn.setFixedWidth(100)
        self.cancel_btn = PushButton("취소")
        self.cancel_btn.setFixedWidth(100)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(btn_layout)
        
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.update_style()
        qconfig.themeChanged.connect(self.update_style)

    def update_style(self):
        from qfluentwidgets import isDarkTheme
        is_dark = isDarkTheme()
        bg_color = "#202020" if is_dark else "#FFFFFF"
        text_color = "#FFFFFF" if is_dark else "#000000"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
        """)
        self.title_label.setStyleSheet(f"color: {text_color}; background: transparent; font-weight: bold;")

    def on_checkbox_changed(self, state):
        if state == Qt.Checked:
            sender = self.sender()
            checked_count = sum(1 for chk in self.checkboxes if chk.isChecked())
            if checked_count > 1:
                sender.blockSignals(True)
                sender.setChecked(False)
                sender.blockSignals(False)
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.warning(
                    title="경고",
                    content="중복 선택할 수 없습니다.",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )

    def get_schedule_data(self):
        start_qdate = self.start_picker.getDate()
        end_qdate = self.end_picker.getDate()
        
        start_str = f"{start_qdate.year()}-{start_qdate.month():02d}-{start_qdate.day():02d}"
        end_str = f"{end_qdate.year()}-{end_qdate.month():02d}-{end_qdate.day():02d}"
        
        if start_str > end_str:
            start_str, end_str = end_str, start_str
            
        text = self.input_edit.text().strip()
        
        prefix = ""
        for chk in self.checkboxes:
            if chk.isChecked():
                prefix = f"[{chk.text()}]"
                break
                
        if prefix and not text.startswith(prefix):
            text = f"{prefix} {text}".strip()
            
        return start_str, end_str, text

    def closeEvent(self, event):
        from qfluentwidgets import qconfig
        try:
            qconfig.themeChanged.disconnect(self.update_style)
        except Exception:
            pass
        super().closeEvent(event)


class FavoriteEditDialog(QDialog):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("즐겨찾기 수정")
        self.setFixedSize(350, 320)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(14)
        
        self.title_label = SubtitleLabel("즐겨찾기 설정", self)
        self.layout.addWidget(self.title_label)
        
        self.inputs = {}
        
        # 키워드
        self.lbl_kw = QLabel("검색 키워드", self)
        self.lbl_kw.setFont(QFont("SUIT", 10, QFont.Bold))
        self.layout.addWidget(self.lbl_kw)
        self.inputs['keyword'] = LineEdit(self)
        self.inputs['keyword'].setPlaceholderText("예: 부산 성형외과")
        if data and 'keyword' in data:
            self.inputs['keyword'].setText(data['keyword'])
        self.layout.addWidget(self.inputs['keyword'])
        
        # 업체명
        self.lbl_cp = QLabel("목표 업체명", self)
        self.lbl_cp.setFont(QFont("SUIT", 10, QFont.Bold))
        self.layout.addWidget(self.lbl_cp)
        self.inputs['company'] = LineEdit(self)
        self.inputs['company'].setPlaceholderText("예: 푸름애드 의원")
        if data and 'company' in data:
            self.inputs['company'].setText(data['company'])
        self.layout.addWidget(self.inputs['company'])
        
        # 탐색 개수
        self.lbl_cnt = QLabel("탐색 목표 개수", self)
        self.lbl_cnt.setFont(QFont("SUIT", 10, QFont.Bold))
        self.layout.addWidget(self.lbl_cnt)
        self.inputs['count'] = SpinBox(self)
        self.inputs['count'].setRange(1, 150)
        self.inputs['count'].setValue(data.get('count', 50) if data else 50)
        self.layout.addWidget(self.inputs['count'])
        
        self.layout.addStretch(1)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch(1)
        
        self.ok_btn = PrimaryPushButton("저장", self)
        self.ok_btn.clicked.connect(self.accept)
        
        self.cancel_btn = PushButton("취소", self)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        self.layout.addLayout(btn_layout)
        
        self.update_style()
        qconfig.themeChanged.connect(self.update_style)
        
    def update_style(self):
        is_dark = isDarkTheme()
        bg_color = "#202020" if is_dark else "#FFFFFF"
        text_color = "#FFFFFF" if is_dark else "#000000"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
        """)
        self.title_label.setStyleSheet(f"color: {text_color}; background: transparent;")
        self.lbl_kw.setStyleSheet(f"color: {text_color}; background: transparent;")
        self.lbl_cp.setStyleSheet(f"color: {text_color}; background: transparent;")
        self.lbl_cnt.setStyleSheet(f"color: {text_color}; background: transparent;")
        
    def get_data(self):
        return {
            'keyword': self.inputs['keyword'].text().strip(),
            'company': self.inputs['company'].text().strip(),
            'count': self.inputs['count'].value()
        }
        
    def closeEvent(self, event):
        try:
            qconfig.themeChanged.disconnect(self.update_style)
        except Exception:
            pass
        super().closeEvent(event)
