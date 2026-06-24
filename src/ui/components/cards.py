import subprocess
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

class MarqueeLabel(QWidget):
    def __init__(self, text, text_color, parent=None):
        super().__init__(parent)
        self.lbl = BodyLabel(text, self)
        self.lbl.setStyleSheet(f"color: {text_color}; font-size: 11px; font-weight: bold; background: transparent; border: none;")
        self.lbl.adjustSize()
        self.offset = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_offset)
        self.is_hovered = False

    def sizeHint(self):
        return self.lbl.sizeHint()

    def minimumSizeHint(self):
        return self.lbl.minimumSizeHint()

    def enterEvent(self, event):
        self.is_hovered = True
        if self.lbl.width() > self.width():
            self.timer.start(30)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.timer.stop()
        self.offset = 0
        y = (self.height() - self.lbl.height()) // 2
        self.lbl.move(0, y)
        super().leaveEvent(event)

    def update_offset(self):
        if self.lbl.width() > self.width():
            self.offset += 1
            if self.offset > self.lbl.width() + 10:
                self.offset = -self.width()
            y = (self.height() - self.lbl.height()) // 2
            self.lbl.move(-self.offset, y)

    def resizeEvent(self, event):
        y = (self.height() - self.lbl.height()) // 2
        if not self.is_hovered:
            self.lbl.move(0, y)
        else:
            self.lbl.move(-self.offset, y)
        super().resizeEvent(event)


class CompanyCard(QFrame):
    def __init__(self, company_data, on_edit, on_delete, parent=None):
        super().__init__(parent)
        self.company_data = company_data
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.setObjectName("CompanyCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        
        # 상단 영역 (업체명 + 수정/삭제 버튼)
        top_layout = QHBoxLayout()
        
        self.name_label = QLabel(company_data.get('name', '업체명 없음'), self)
        self.name_label.setFont(QFont("SUIT", 16, QFont.Bold))
        top_layout.addWidget(self.name_label)
        
        top_layout.addStretch(1)
        
        self.edit_btn = TransparentToolButton(FluentIcon.EDIT, self)
        self.edit_btn.setFixedSize(30, 30)
        self.edit_btn.clicked.connect(self.on_edit)
        top_layout.addWidget(self.edit_btn)
        
        self.delete_btn = TransparentToolButton(FluentIcon.DELETE, self)
        self.delete_btn.setFixedSize(30, 30)
        self.delete_btn.clicked.connect(self.on_delete)
        top_layout.addWidget(self.delete_btn)
        
        layout.addLayout(top_layout)
        
        # 하단 영역 (링크들)
        links_layout = QHBoxLayout()
        links_layout.setSpacing(24)
        
        self.link_configs = [
            ('homepage', '홈페이지'),
            ('place', '플레이스'),
            ('blog1', '블로그1'),
            ('blog2', '블로그2'),
            ('instagram', '인스타그램')
        ]
        
        self.buttons = []
        for key, display_name in self.link_configs:
            btn = PushButton(display_name, self)
            url = company_data.get(key, '').strip()
            if url:
                btn.setEnabled(True)
                btn.clicked.connect(lambda checked, u=url: self.open_link(u))
            else:
                btn.setEnabled(False)
                
            links_layout.addWidget(btn)
            self.buttons.append((btn, url))
            
        links_layout.addStretch(1)
        layout.addLayout(links_layout)
        
        self.update_style()
        qconfig.themeChanged.connect(self.update_style)
        
    def update_style(self):
        is_dark = isDarkTheme()
        bg_color = "#2C2C2C" if is_dark else "#F3F3F3"
        border_color = "#3A3A3A" if is_dark else "#E5E5E5"
        hover_bg = "#383838" if is_dark else "#EBEBEB"
        hover_border = "#4D4D4D" if is_dark else "#D8D8D8"
        text_color = "#FFFFFF" if is_dark else "#000000"
        
        link_color = "#60CDFF" if is_dark else "#0078D4"
        link_hover_color = "#A6E2FF" if is_dark else "#005A9E"
        link_disabled_color = "#666666" if is_dark else "#B0B0B0"
        
        self.setStyleSheet(f"""
            QFrame#CompanyCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 16px;
            }}
            QFrame#CompanyCard:hover {{
                background-color: {hover_bg};
                border: 1px solid {hover_border};
            }}
        """)
        self.name_label.setStyleSheet(f"background: transparent; color: {text_color};")
        
        for btn, url in self.buttons:
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {link_color};
                    background: transparent;
                    border: none;
                    font-family: 'SUIT';
                    font-size: 14px;
                    font-weight: 500;
                    padding: 2px 6px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    color: {link_hover_color};
                    text-decoration: underline;
                    background: transparent;
                }}
                QPushButton:disabled {{
                    color: {link_disabled_color};
                    background: transparent;
                }}
            """)
            
    def open_link(self, url):
        if not url:
            return
        url = url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
        QDesktopServices.openUrl(QUrl(url))
        
    def closeEvent(self, event):
        try:
            qconfig.themeChanged.disconnect(self.update_style)
        except Exception:
            pass
        super().closeEvent(event)


class HolidayCheckCard(QFrame):
    def __init__(self, company_data, date_str, check_data, on_changed, parent=None):
        super().__init__(parent)
        self.company_data = company_data
        self.date_str = date_str
        self.check_data = check_data  # {"place_checked": bool, "place_reason": str, "popup_checked": bool, "popup_reason": str}
        self.on_changed = on_changed
        self.setObjectName("HolidayCheckCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        
        # Row 1: Company Name
        self.name_label = QLabel(company_data.get('name', '업체명 없음'), self)
        self.name_label.setFont(QFont("SUIT", 12, QFont.Bold))
        layout.addWidget(self.name_label)
        
        # Row 2: Verification Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        # 1) Place Section
        self.place_btn = QPushButton("플레이스", self)
        self.place_btn.setCursor(Qt.PointingHandCursor)
        place_url = company_data.get('place', '').strip()
        if place_url:
            self.place_btn.setEnabled(True)
            self.place_btn.clicked.connect(lambda checked, u=place_url: self.open_link(u))
        else:
            self.place_btn.setEnabled(False)
            self.place_btn.setCursor(Qt.ArrowCursor)
            
        controls_layout.addWidget(self.place_btn)
        
        self.place_input = LineEdit(self)
        self.place_input.setPlaceholderText("사유")
        self.place_input.setText(check_data.get('place_reason', ''))
        self.place_input.setFixedWidth(90)
        self.place_input.textEdited.connect(self.notify_change)
        controls_layout.addWidget(self.place_input)
        
        self.place_chk_btn = QPushButton(self)
        self.place_chk_btn.setFixedSize(24, 24)
        is_place_checked = check_data.get('place_checked', True)
        self.set_toggle_style(self.place_chk_btn, is_place_checked)
        self.place_chk_btn.clicked.connect(self.toggle_place_status)
        controls_layout.addWidget(self.place_chk_btn)
        
        # Spacer
        controls_layout.addSpacing(16)
        
        # 2) Popup Section
        self.popup_btn = QPushButton("팝업", self)
        self.popup_btn.setCursor(Qt.PointingHandCursor)
        popup_url = company_data.get('homepage', '').strip()
        if popup_url:
            self.popup_btn.setEnabled(True)
            self.popup_btn.clicked.connect(lambda checked, u=popup_url: self.open_link(u))
        else:
            self.popup_btn.setEnabled(False)
            self.popup_btn.setCursor(Qt.ArrowCursor)
            
        controls_layout.addWidget(self.popup_btn)
        
        self.popup_input = LineEdit(self)
        self.popup_input.setPlaceholderText("사유")
        self.popup_input.setText(check_data.get('popup_reason', ''))
        self.popup_input.setFixedWidth(90)
        self.popup_input.textEdited.connect(self.notify_change)
        controls_layout.addWidget(self.popup_input)
        
        self.popup_chk_btn = QPushButton(self)
        self.popup_chk_btn.setFixedSize(24, 24)
        is_popup_checked = check_data.get('popup_checked', True)
        self.set_toggle_style(self.popup_chk_btn, is_popup_checked)
        self.popup_chk_btn.clicked.connect(self.toggle_popup_status)
        controls_layout.addWidget(self.popup_chk_btn)
        
        controls_layout.addStretch(1)
        layout.addLayout(controls_layout)
        
        self.update_style()
        qconfig.themeChanged.connect(self.update_style)
        
    def set_toggle_style(self, btn, is_checked):
        btn.setProperty("checked_state", is_checked)
        if is_checked:
            btn.setText("✔")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #25A662;
                    color: white;
                    font-family: 'SUIT';
                    font-size: 12px;
                    font-weight: bold;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #1D8B52;
                }
            """)
        else:
            btn.setText("X")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #E81123;
                    color: white;
                    font-family: 'SUIT';
                    font-size: 12px;
                    font-weight: bold;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #D10F20;
                }
            """)
            
    def update_style(self):
        is_dark = isDarkTheme()
        bg_color = "#2C2C2C" if is_dark else "#F3F3F3"
        border_color = "#3A3A3A" if is_dark else "#E5E5E5"
        text_color = "#FFFFFF" if is_dark else "#000000"
        
        link_color = "#60CDFF" if is_dark else "#0078D4"
        link_hover_color = "#A6E2FF" if is_dark else "#005A9E"
        link_disabled_color = "#666666" if is_dark else "#B0B0B0"
        
        self.setStyleSheet(f"""
            QFrame#HolidayCheckCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
        self.name_label.setStyleSheet(f"background: transparent; color: {text_color};")
        
        for btn in [self.place_btn, self.popup_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {link_color};
                    background: transparent;
                    border: none;
                    font-family: 'SUIT';
                    font-size: 15px;
                    font-weight: bold;
                    padding: 2px 4px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    color: {link_hover_color};
                    text-decoration: underline;
                    background: transparent;
                }}
                QPushButton:disabled {{
                    color: {link_disabled_color};
                    background: transparent;
                }}
            """)
            
        input_bg = "#161616" if is_dark else "#FFFFFF"
        input_fg = "#FFFFFF" if is_dark else "#000000"
        input_border = "#3A3A3A" if is_dark else "#CCCCCC"
        input_style = f"""
            QLineEdit {{
                background-color: {input_bg} !important;
                color: {input_fg} !important;
                border: 1px solid {input_border};
                border-radius: 4px;
                font-family: 'SUIT';
                font-size: 14px;
                font-weight: bold;
                padding: 2px 4px;
            }}
            QLineEdit:focus {{
                border: 1px solid {link_color};
            }}
        """
        self.place_input.setStyleSheet(input_style)
        self.popup_input.setStyleSheet(input_style)
            
    def toggle_place_status(self):
        current = self.place_chk_btn.property("checked_state")
        self.set_toggle_style(self.place_chk_btn, not current)
        self.notify_change()
        
    def toggle_popup_status(self):
        current = self.popup_chk_btn.property("checked_state")
        self.set_toggle_style(self.popup_chk_btn, not current)
        self.notify_change()
        
    def notify_change(self):
        data = {
            "place_checked": self.place_chk_btn.property("checked_state"),
            "place_reason": self.place_input.text().strip(),
            "popup_checked": self.popup_chk_btn.property("checked_state"),
            "popup_reason": self.popup_input.text().strip()
        }
        self.on_changed(self.company_data.get('name', ''), data)
        
    def open_link(self, url):
        if not url:
            return
        url = url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
        QDesktopServices.openUrl(QUrl(url))
        
    def closeEvent(self, event):
        try:
            qconfig.themeChanged.disconnect(self.update_style)
        except Exception:
            pass
        super().closeEvent(event)


class ExposureCard(QFrame):
    def __init__(self, match_data, parent=None):
        super().__init__(parent)
        self.match_data = match_data  # {'company': ..., 'keyword': ..., 'ranks': [...], 'screenshots': [...], 'folder': ...}
        self.setObjectName("ExposureCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        
        # Header (업체명 + 키워드 + 바로가기)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        self.company_label = QLabel(match_data.get('company', '업체명 없음'), self)
        self.company_label.setFont(QFont("SUIT", 12, QFont.Bold))
        header_layout.addWidget(self.company_label)
        
        self.keyword_label = QLabel(match_data.get('keyword', '키워드 없음'), self)
        self.keyword_label.setFont(QFont("SUIT", 11, QFont.Bold))
        header_layout.addWidget(self.keyword_label)
        
        header_layout.addStretch(1)
        
        self.shortcut_btn = PushButton("스크린샷 바로가기", self)
        self.shortcut_btn.clicked.connect(self.open_folder)
        header_layout.addWidget(self.shortcut_btn)
        
        layout.addLayout(header_layout)
        
        # Ranks box
        self.ranks_box = QFrame(self)
        self.ranks_box.setObjectName("RanksBox")
        box_layout = QHBoxLayout(self.ranks_box)
        box_layout.setContentsMargins(12, 6, 12, 6)
        box_layout.setSpacing(16)
        
        # Add rank buttons
        self.rank_buttons = []
        for rank, path in match_data.get('screenshots', []):
            btn = PushButton(f"{rank}위", self.ranks_box)
            btn.setFont(QFont("SUIT", 11, QFont.Bold))
            btn.clicked.connect(lambda checked, p=path: self.open_screenshot(p))
            box_layout.addWidget(btn)
            self.rank_buttons.append((btn, path))
            
        box_layout.addStretch(1)
        layout.addWidget(self.ranks_box)
        
        self.update_style()
        qconfig.themeChanged.connect(self.update_style)
        
    def update_style(self):
        is_dark = isDarkTheme()
        
        # Main card colors
        bg_color = "#2C2C2C" if is_dark else "#F3F3F3"
        border_color = "#3A3A3A" if is_dark else "#E5E5E5"
        text_color = "#FFFFFF" if is_dark else "#000000"
        sub_text_color = "#CCCCCC" if is_dark else "#333333"
        
        # Ranks box colors
        box_bg = "#161616" if is_dark else "#E5E5E5"
        btn_fg = "#FFFFFF" if is_dark else "#000000"
        btn_hover_fg = "#E0E0E0" if is_dark else "#0078D4"
        
        self.setStyleSheet(f"""
            QFrame#ExposureCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
        self.company_label.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
        self.keyword_label.setStyleSheet(f"color: {sub_text_color}; background: transparent; border: none;")
        
        # Shortcut button style
        link_color = "#60CDFF" if is_dark else "#0078D4"
        link_hover_color = "#A6E2FF" if is_dark else "#005A9E"
        self.shortcut_btn.setStyleSheet(f"""
            QPushButton {{
                color: {link_color};
                background: transparent;
                border: none;
                font-family: 'SUIT';
                font-size: 11px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                color: {link_hover_color};
                text-decoration: underline;
                background: transparent;
            }}
        """)
        
        # Ranks box stylesheet
        self.ranks_box.setStyleSheet(f"""
            QFrame#RanksBox {{
                background-color: {box_bg};
                border-radius: 8px;
                border: none;
            }}
        """)
        
        # Rank buttons style
        for btn, _ in self.rank_buttons:
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {btn_fg};
                    background: transparent;
                    border: none;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    text-decoration: underline;
                    color: {btn_hover_fg};
                    background: transparent;
                }}
            """)
            
    def open_folder(self):
        folder = self.match_data.get('folder', '')
        if folder and os.path.exists(folder):
            os.startfile(folder)
        else:
            InfoBar.warning("안내", "스크린샷이 없습니다!", duration=3000, parent=self)
            
    def open_screenshot(self, filepath):
        if filepath and os.path.exists(filepath):
            subprocess.Popen(f'explorer /select,"{os.path.abspath(filepath)}"')
        else:
            InfoBar.warning("안내", "스크린샷이 없습니다!", duration=3000, parent=self)
            
    def closeEvent(self, event):
        try:
            qconfig.themeChanged.disconnect(self.update_style)
        except Exception:
            pass
        super().closeEvent(event)


class FeatureCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, icon, title, content, parent=None):
        super().__init__(parent)
        self.icon_widget = IconWidget(icon)
        
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("SUIT", 14, QFont.Bold))
        self.title_label.setStyleSheet("color: #EAEAEA; background: transparent;")
        
        self.content_label = QLabel(content)
        self.content_label.setFont(QFont("SUIT", 10))
        self.content_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); background: transparent;")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        
        header_layout = QHBoxLayout()
        self.icon_widget.setFixedSize(28, 28)
        header_layout.addWidget(self.icon_widget)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.content_label)
        layout.addStretch(1)
        
        self.setFixedSize(280, 120)
        self.setObjectName("FeatureCard")
        self.setStyleSheet("""
            #FeatureCard {
                background-color: rgba(30, 30, 35, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
            }
            #FeatureCard:hover {
                background-color: rgba(45, 45, 50, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.25);
            }
        """)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit()


class MonthlyScheduleSummaryCard(QFrame):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("MonthlyScheduleSummaryCard")
        self.setStyleSheet("""
            QFrame#MonthlyScheduleSummaryCard {
                background-color: #2C2C2C;
                border: 1px solid #3A3A3A;
                border-radius: 10px;
            }
            QFrame#MonthlyScheduleSummaryCard:hover {
                background-color: #333333;
                border: 1px solid #444444;
            }
        """)
        self.setFixedSize(280, 120)
        
        from PyQt5.QtCore import Qt
        self.setCursor(Qt.PointingHandCursor)
        
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(16, 16, 16, 16)
        self.vBoxLayout.setSpacing(8)
        
        title_layout = QHBoxLayout()
        title_icon = IconWidget(FluentIcon.CALENDAR)
        title_icon.setFixedSize(24, 24)
        
        from datetime import date
        today_date_str = date.today().strftime('%m/%d')
        title_label = QLabel(f"{today_date_str} 오늘의 일정")
        from PyQt5.QtGui import QFont
        title_label.setFont(QFont("SUIT", 14, QFont.Bold))
        title_label.setStyleSheet("color: #EAEAEA; background: transparent;")
        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch(1)
        
        self.vBoxLayout.addLayout(title_layout)
        
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(2)
        self.vBoxLayout.addLayout(self.content_layout)
        
        self.vBoxLayout.addStretch(1)
        
        self.loading_label = QLabel("데이터를 불러오는 중...")
        self.loading_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); background: transparent;")
        from PyQt5.QtGui import QFont
        self.loading_label.setFont(QFont("SUIT", 10))
        self.content_layout.addWidget(self.loading_label)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.main_window.switchTo(self.main_window.schedule_interface)

    def go_to_calendar(self):
        # Programmatically switch to schedule tab
        # main_window.stackedWidget.setCurrentWidget(main_window.schedule_interface)
        # However, it's a bit tricky due to FluentWindow internal routing. We can do:
        self.main_window.switchTo(self.main_window.schedule_interface)

    def update_schedule(self, schedules):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not schedules:
            no_lbl = QLabel("오늘 예정된 연차 또는 일정이 없습니다.")
            no_lbl.setStyleSheet("color: #A0A0A0;")
            self.content_layout.addWidget(no_lbl)
            return
            
        
        max_items = 2
        for i, sch in enumerate(schedules):
            if i >= max_items:
                more_lbl = QLabel(f"...외 {len(schedules) - max_items}개")
                more_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
                self.content_layout.addWidget(more_lbl)
                break
                
            text = sch[0] if isinstance(sch, tuple) else sch
            color = sch[1] if isinstance(sch, tuple) else "#1976D2"
            
            try:
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                text_color = "#000000" if luminance > 0.5 else "#ffffff"
            except:
                text_color = "#000000"
                
            lbl = QLabel(text)
            lbl.setStyleSheet(f"background-color: {color}; color: {text_color}; border-radius: 4px; padding: 1px 6px; font-size: 11px; font-weight: bold;")
            self.content_layout.addWidget(lbl)


class SpellCheckIssueCard(QFrame):
    def __init__(self, issue, parent=None):
        super().__init__(parent)
        self.issue = issue  # SpellCheckIssue
        self.setObjectName("SpellCheckIssueCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        top_layout = QHBoxLayout()
        
        org_label = QLabel(issue.original, self)
        org_label.setFont(QFont("SUIT", 12, QFont.Bold))
        org_label.setStyleSheet("color: #FF6B6B; text-decoration: line-through; background: transparent; border: none;")
        top_layout.addWidget(org_label)
        
        arrow_label = QLabel("→", self)
        arrow_label.setFont(QFont("SUIT", 12, QFont.Bold))
        arrow_label.setStyleSheet("color: #A0A0A0; background: transparent; border: none;")
        top_layout.addWidget(arrow_label)
        
        sug_text = issue.suggestions[0] if issue.suggestions else "(없음)"
        sug_label = QLabel(sug_text, self)
        sug_label.setFont(QFont("SUIT", 12, QFont.Bold))
        sug_label.setStyleSheet("color: #40C463; background: transparent; border: none;")
        top_layout.addWidget(sug_label)
        
        top_layout.addStretch(1)
        layout.addLayout(top_layout)
        
        if issue.reason:
            reason_label = QLabel(issue.reason, self)
            reason_label.setFont(QFont("SUIT", 11))
            reason_label.setWordWrap(True)
            reason_label.setStyleSheet("color: #E5E5E5; background: transparent; border: none; line-height: 1.4;")
            layout.addWidget(reason_label)
            
        self.update_style()
        qconfig.themeChanged.connect(self.update_style)
        
    def update_style(self):
        is_dark = isDarkTheme()
        bg_color = "#2C2C2C" if is_dark else "#FFFFFF"
        border_color = "#3A3A3A" if is_dark else "#E5E5E5"
        self.setStyleSheet(f"""
            QFrame#SpellCheckIssueCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
        """)


class PlaceExposureCard(QFrame):
    def __init__(self, match_data, parent=None):
        super().__init__(parent)
        self.match_data = match_data  
        self.setObjectName("PlaceExposureCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        self.company_label = QLabel(match_data.get('company', ''), self)
        self.company_label.setFont(QFont("SUIT", 12, QFont.Bold))
        header_layout.addWidget(self.company_label)
        
        self.keyword_label = QLabel(match_data.get('keyword', ''), self)
        self.keyword_label.setFont(QFont("SUIT", 11, QFont.Bold))
        header_layout.addWidget(self.keyword_label)
        
        header_layout.addStretch(1)
        layout.addLayout(header_layout)
        
        self.ranks_box = QFrame(self)
        self.ranks_box.setObjectName("RanksBox")
        box_layout = QHBoxLayout(self.ranks_box)
        box_layout.setContentsMargins(12, 6, 12, 6)
        box_layout.setSpacing(16)
        
        for rank in match_data.get('ranks', []):
            lbl = QLabel(f"{rank}위", self.ranks_box)
            lbl.setFont(QFont("SUIT", 11, QFont.Bold))
            lbl.setStyleSheet("color: #60CDFF; background: transparent; border: none;")
            box_layout.addWidget(lbl)
            
        box_layout.addStretch(1)
        layout.addWidget(self.ranks_box)
        
        self.update_style()
        qconfig.themeChanged.connect(self.update_style)
        
    def update_style(self):
        is_dark = isDarkTheme()
        bg_color = "#2C2C2C" if is_dark else "#F3F3F3"
        border_color = "#3A3A3A" if is_dark else "#E5E5E5"
        text_color = "#FFFFFF" if is_dark else "#000000"
        sub_text_color = "#CCCCCC" if is_dark else "#333333"
        box_bg = "#161616" if is_dark else "#E5E5E5"
        
        self.setStyleSheet(f"""
            QFrame#PlaceExposureCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
            QFrame#RanksBox {{
                background-color: {box_bg};
                border-radius: 8px;
            }}
        """)
        self.company_label.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
        self.keyword_label.setStyleSheet(f"color: {sub_text_color}; background: transparent; border: none;")


class ScheduleItemWidget(QFrame):
    delete_requested = pyqtSignal(str, str)
    
    def __init__(self, date_str, text, color, text_color, creator_id=None):
        super().__init__()
        self.date_str = date_str
        self.raw_text = text
        self.creator_id = creator_id
        self.setStyleSheet(f"background-color: {color}; color: {text_color}; border-radius: 4px;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 1, 6, 1)
        
        self.lbl = MarqueeLabel(text, text_color, self)
        self.lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(self.lbl)
        
    def contextMenuEvent(self, event):
        from qfluentwidgets import RoundMenu, Action, InfoBar, InfoBarPosition
        from PyQt5.QtCore import QTimer
        
        global SESSION
        my_id = str(SESSION.get("id") or "").strip()
        c_id = str(self.creator_id or "").strip()
        if not my_id or my_id != c_id:
            return

        menu = RoundMenu(parent=self)
        delete_action = Action(FluentIcon.DELETE, '삭제', self)
        delete_action.triggered.connect(lambda: QTimer.singleShot(0, lambda: self.delete_requested.emit(self.date_str, self.raw_text)))
        menu.addAction(delete_action)
        menu.exec(event.globalPos())

class FavoritePlaceCard(QFrame):
    double_clicked = pyqtSignal(int)
    single_clicked = pyqtSignal(int)
    cancel_clicked = pyqtSignal(int)
    
    def __init__(self, index, data, parent=None):
        super().__init__(parent)
        self.index = index
        self.data = data
        self.status = "idle" # idle, queued, running, done
        self.setObjectName("FavoritePlaceCard")
        
        self.setFixedSize(140, 100)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        self.keyword_label = QLabel(self.data.get('keyword', '설정 안됨'), self)
        self.keyword_label.setFont(QFont("SUIT", 10, QFont.Bold))
        self.keyword_label.setAlignment(Qt.AlignCenter)
        self.keyword_label.setWordWrap(True)
        
        self.company_label = QLabel(self.data.get('company', '더블클릭하여 설정'), self)
        self.company_label.setFont(QFont("SUIT", 9))
        self.company_label.setAlignment(Qt.AlignCenter)
        self.company_label.setWordWrap(True)
        
        self.result_label = QLabel("", self)
        self.result_label.setFont(QFont("SUIT", 11, QFont.Bold))
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("color: #60CDFF; background: transparent; border: none;")
        self.result_label.hide()
        
        self.loading_ring = IndeterminateProgressRing(self)
        self.loading_ring.setFixedSize(20, 20)
        self.loading_ring.hide()
        
        top_layout = QHBoxLayout()
        top_layout.addStretch(1)
        top_layout.addWidget(self.loading_ring)
        top_layout.addStretch(1)
        
        layout.addStretch(1)
        layout.addWidget(self.keyword_label)
        layout.addWidget(self.company_label)
        layout.addLayout(top_layout)
        layout.addWidget(self.result_label)
        layout.addStretch(1)
        
        self.update_style()
        qconfig.themeChanged.connect(self.update_style)
        
    def update_style(self):
        is_dark = isDarkTheme()
        
        if self.status == "queued":
            bg_color = "#3A2E12" if is_dark else "#FFF4CE"
            border_color = "#FFA000"
            text_color = "#FFFFFF" if is_dark else "#000000"
        elif self.status == "running":
            bg_color = "#1E2D3D" if is_dark else "#CCE4F7"
            border_color = "#0078D4"
            text_color = "#FFFFFF" if is_dark else "#000000"
        else:
            bg_color = "#2C2C2C" if is_dark else "#F3F3F3"
            border_color = "#3A3A3A" if is_dark else "#E5E5E5"
            text_color = "#FFFFFF" if is_dark else "#000000"
            
        sub_text_color = "#CCCCCC" if is_dark else "#333333"
        hover_bg = "#383838" if is_dark else "#EBEBEB"
        if self.status in ["queued", "running"]:
            hover_bg = bg_color # No hover change while running/queued
            
        self.setStyleSheet(f"""
            QFrame#FavoritePlaceCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
            QFrame#FavoritePlaceCard:hover {{
                background-color: {hover_bg};
            }}
        """)
        self.keyword_label.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
        self.company_label.setStyleSheet(f"color: {sub_text_color}; background: transparent; border: none;")
        
    def update_data(self, data):
        self.data = data
        self.keyword_label.setText(self.data.get('keyword', '설정 안됨') or '설정 안됨')
        self.company_label.setText(self.data.get('company', '더블클릭하여 설정') or '더블클릭하여 설정')
        self.set_status("idle")
        
    def set_status(self, status, ranks=None):
        self.status = status
        if status == "running":
            self.loading_ring.start()
            self.loading_ring.show()
            self.result_label.hide()
        elif status == "queued":
            self.loading_ring.stop()
            self.loading_ring.hide()
            self.result_label.setText("대기 중")
            self.result_label.setStyleSheet("color: #FFA000; background: transparent; border: none;")
            self.result_label.show()
        elif status == "done":
            self.loading_ring.stop()
            self.loading_ring.hide()
            if ranks:
                rank_str = ", ".join([f"{r}위" for r in ranks])
                self.result_label.setText(rank_str)
                self.result_label.setStyleSheet("color: #60CDFF; background: transparent; border: none;")
            else:
                self.result_label.setText("미노출")
                self.result_label.setStyleSheet("color: #FF6B6B; background: transparent; border: none;")
            self.result_label.show()
        else:
            self.loading_ring.stop()
            self.loading_ring.hide()
            self.result_label.hide()
            
        self.update_style()
        
    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.double_clicked.emit(self.index)
        
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.data.get('keyword'):
            if self.status in ["queued", "running"]:
                self.cancel_clicked.emit(self.index)
            else:
                self.single_clicked.emit(self.index)
            
    def closeEvent(self, event):
        try:
            qconfig.themeChanged.disconnect(self.update_style)
        except Exception:
            pass
        super().closeEvent(event)

class CrossCheckListCard(QFrame):
    clicked = pyqtSignal(dict)
    
    def __init__(self, company_data, cross_check_data, parent=None):
        super().__init__(parent)
        self.company_data = company_data
        self.cross_check_data = cross_check_data
        self.setObjectName("CrossCheckListCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(70)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        
        self.name_label = QLabel(company_data.get('name', ''), self)
        self.name_label.setFont(QFont("SUIT", 12, QFont.Bold))
        layout.addWidget(self.name_label)
        
        self.summary_label = QLabel(self)
        self.summary_label.setFont(QFont("SUIT", 10))
        layout.addWidget(self.summary_label)
        
        self.update_summary(cross_check_data)
        self.is_selected = False
        self.update_style()
        try:
            qconfig.themeChanged.connect(self.update_style)
        except Exception:
            pass
        
    def update_summary(self, cross_check_data):
        self.cross_check_data = cross_check_data
        if not cross_check_data or "users" not in cross_check_data:
            self.summary_label.setText("기록 없음")
            return
            
        summary_parts = []
        for user, checks in cross_check_data["users"].items():
            pc = checks.get("popup_check", "")
            plc = checks.get("place_check", "")
            if pc or plc:
                part = f"{user}:"
                if pc: part += f"팝({pc})"
                if plc: part += f"플({plc})"
                summary_parts.append(part)
                
        if summary_parts:
            self.summary_label.setText(" | ".join(summary_parts))
        else:
            self.summary_label.setText("기록 없음")
            
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit(self.company_data)
        
    def set_selected(self, selected):
        self.is_selected = selected
        self.update_style()
        
    def update_style(self):
        is_dark = isDarkTheme()
        bg_color = "#2C2C2C" if is_dark else "#FFFFFF"
        border_color = "#3A3A3A" if is_dark else "#E5E5E5"
        hover_bg = "#383838" if is_dark else "#F9F9F9"
        text_color = "#FFFFFF" if is_dark else "#000000"
        
        if getattr(self, 'is_selected', False):
            bg_color = "#1E2D3D" if is_dark else "#CCE4F7"
            border_color = "#0078D4"
            
        self.setStyleSheet(f"""
            QFrame#CrossCheckListCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QFrame#CrossCheckListCard:hover {{
                background-color: {hover_bg};
            }}
        """)
        self.name_label.setStyleSheet(f"background: transparent; color: {text_color};")
        self.summary_label.setStyleSheet("background: transparent; color: #888888;")
        
    def closeEvent(self, event):
        try:
            qconfig.themeChanged.disconnect(self.update_style)
        except Exception:
            pass
        super().closeEvent(event)
