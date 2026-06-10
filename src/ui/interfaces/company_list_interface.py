from src.utils.helpers import load_companies, save_companies, load_holiday_checks, save_holiday_checks, get_korean_holidays

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
from src.ui.components.dialogs import CompanyDialog
from src.ui.components.cards import HolidayCheckCard, CompanyCard
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, FONT_DIR, SETTINGS_PATH, CREDENTIALS_PATH

class CompanyListInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("CompanyListInterface")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 36, 36, 36)
        main_layout.setSpacing(16)
        
        # Header (Title + Buttons)
        header_layout = QHBoxLayout()
        self.title_label = TitleLabel("업체 리스트", self)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch(1)
        
        self.add_btn = PushButton("업체 추가", self)
        self.add_btn.setIcon(FluentIcon.ADD)
        self.add_btn.clicked.connect(self.add_company)
        header_layout.addWidget(self.add_btn)
        
        # Holiday Check Button next to Add Company (reordered to the right)
        self.holiday_btn = PushButton("휴진 체크", self)
        self.holiday_btn.setIcon(FluentIcon.CALENDAR)
        self.holiday_btn.clicked.connect(self.toggle_holiday_panel)
        header_layout.addWidget(self.holiday_btn)
        
        main_layout.addLayout(header_layout)
        
        # Content layout (Split layout)
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(24)
        
        # Left Panel: Scroll Area for Card List
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_content.setStyleSheet("QWidget#ScrollContent { background: transparent; }")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 10, 0)
        self.scroll_layout.setSpacing(16)
        
        self.scroll_area.setWidget(self.scroll_content)
        self.content_layout.addWidget(self.scroll_area, 3) # Stretch 3
        
        # Right Panel: Holiday Check Panel
        self.holiday_panel = QWidget(self)
        self.holiday_panel.setObjectName("HolidayPanel")
        self.holiday_panel_layout = QVBoxLayout(self.holiday_panel)
        self.holiday_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.holiday_panel_layout.setSpacing(16)
        
        # 1. Calendar Widget
        self.calendar = QCalendarWidget(self.holiday_panel)
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.selectionChanged.connect(self.render_holiday_checks)
        self.calendar.currentPageChanged.connect(self.update_calendar_holidays)
        self.holiday_panel_layout.addWidget(self.calendar)
        
        # Add "오늘" button to calendar navigation bar
        nav_bar = self.calendar.findChild(QWidget, "qt_calendar_navigationbar")
        if nav_bar:
            layout = nav_bar.layout()
            if layout:
                self.today_btn = QPushButton("오늘", nav_bar)
                self.today_btn.setFixedSize(45, 24)
                self.today_btn.setCursor(Qt.PointingHandCursor)
                self.today_btn.clicked.connect(self.go_to_today)
                layout.insertWidget(layout.count() - 1, self.today_btn)
        
        # 2. Holiday checklist title and export button (QHBoxLayout)
        title_layout = QHBoxLayout()
        self.holiday_list_title = SubtitleLabel("휴진 체크 리스트", self.holiday_panel)
        self.holiday_list_title.setFont(QFont("SUIT", 12, QFont.Bold))
        title_layout.addWidget(self.holiday_list_title)
        
        title_layout.addStretch(1)
        
        self.export_btn = PushButton("메모장 내보내기", self.holiday_panel)
        self.export_btn.setIcon(FluentIcon.SHARE)
        self.export_btn.setFixedSize(160, 28)
        self.export_btn.setFont(QFont("SUIT", 9, QFont.Bold))
        self.export_btn.clicked.connect(self.export_holiday_checks)
        title_layout.addWidget(self.export_btn)
        
        self.holiday_panel_layout.addLayout(title_layout)
        
        # 3. Checklist Scroll Area
        self.holiday_list_scroll = ScrollArea(self.holiday_panel)
        self.holiday_list_scroll.setWidgetResizable(True)
        
        self.holiday_list_content = QWidget()
        self.holiday_list_content.setObjectName("HolidayListContent")
        self.holiday_list_content.setStyleSheet("QWidget#HolidayListContent { background: transparent; }")
        self.holiday_list_layout = QVBoxLayout(self.holiday_list_content)
        self.holiday_list_layout.setContentsMargins(12, 12, 12, 12)
        self.holiday_list_layout.setSpacing(12)
        
        self.holiday_list_scroll.setWidget(self.holiday_list_content)
        self.holiday_panel_layout.addWidget(self.holiday_list_scroll)
        
        self.content_layout.addWidget(self.holiday_panel, 2) # Stretch 2
        
        main_layout.addLayout(self.content_layout)
        
        # Hide holiday panel by default
        self.holiday_panel.setVisible(False)
        
        # Load and render initial list
        self.companies = load_companies()
        self.render_list()
        
        # Styling & Holiday markings setup
        self.update_holiday_panel_style()
        self.update_calendar_style()
        self.update_calendar_holidays()
        qconfig.themeChanged.connect(self.update_holiday_panel_style)
        qconfig.themeChanged.connect(self.update_calendar_style)
        qconfig.themeChanged.connect(self.update_calendar_holidays)
        
    def render_list(self):
        # Clear existing layout
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # Create a card for each company
        for idx, company in enumerate(self.companies):
            card = CompanyCard(
                company, 
                on_edit=lambda checked, i=idx: self.edit_company(i),
                on_delete=lambda checked, i=idx: self.delete_company(i),
                parent=self.scroll_content
            )
            self.scroll_layout.addWidget(card)
            
        self.scroll_layout.addStretch(1)
        
        # Sync holiday check list if panel is visible
        if hasattr(self, 'holiday_panel') and self.holiday_panel.isVisible():
            self.render_holiday_checks()
            
    def toggle_holiday_panel(self):
        is_visible = not self.holiday_panel.isVisible()
        self.holiday_panel.setVisible(is_visible)
        if is_visible:
            self.render_holiday_checks()
            self.update_calendar_holidays()
            
    def render_holiday_checks(self):
        while self.holiday_list_layout.count():
            child = self.holiday_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        selected_date_str = self.calendar.selectedDate().toString("yyyy-MM-dd")
        all_checks = load_holiday_checks()
        date_checks = all_checks.get(selected_date_str, {})
        
        # Reload companies to reflect updates/deletes/additions
        self.companies = load_companies()
        
        for company in self.companies:
            comp_name = company.get('name', '')
            comp_checks = date_checks.get(comp_name, {
                "place_checked": True,
                "place_reason": "",
                "popup_checked": True,
                "popup_reason": ""
            })
            
            card = HolidayCheckCard(
                company_data=company,
                date_str=selected_date_str,
                check_data=comp_checks,
                on_changed=lambda name, data: self.save_company_check(selected_date_str, name, data),
                parent=self.holiday_list_content
            )
            self.holiday_list_layout.addWidget(card)
            
        self.holiday_list_layout.addStretch(1)
        
    def save_company_check(self, date_str, company_name, check_data):
        all_checks = load_holiday_checks()
        if date_str not in all_checks:
            all_checks[date_str] = {}
        all_checks[date_str][company_name] = check_data
        save_holiday_checks(all_checks)
        
    def export_holiday_checks(self):
        selected_date_str = self.calendar.selectedDate().toString("yyyy-MM-dd")
        all_checks = load_holiday_checks()
        date_checks = all_checks.get(selected_date_str, {})
        
        self.companies = load_companies()
        if not self.companies:
            InfoBar.warning("안내", "내보낼 업체 데이터가 없습니다.", duration=3000, parent=self)
            return
            
        lines = [f"[{selected_date_str} 휴진 체크 리스트]\n"]
        for company in self.companies:
            name = company.get('name', '업체명 없음')
            comp_checks = date_checks.get(name, {
                "place_checked": True,
                "place_reason": "",
                "popup_checked": True,
                "popup_reason": ""
            })
            
            lines.append(f"●{name}")
            
            # Place Status (O / X)
            place_ok = "O" if comp_checks.get("place_checked", True) else "X"
            place_reason = comp_checks.get("place_reason", "").strip()
            place_suffix = f" ({place_reason})" if place_reason else ""
            lines.append(f"플레이스 : {place_ok}{place_suffix}")
            
            # Popup Status (O / X)
            popup_ok = "O" if comp_checks.get("popup_checked", True) else "X"
            popup_reason = comp_checks.get("popup_reason", "").strip()
            popup_suffix = f" ({popup_reason})" if popup_reason else ""
            lines.append(f"팝업 : {popup_ok}{popup_suffix}\n")
            
        export_text = "\n".join(lines)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "메모장 내보내기",
            f"휴진체크_{selected_date_str}.txt",
            "텍스트 파일 (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(export_text)
                InfoBar.success("성공", "텍스트 파일이 저장되었습니다.", duration=3000, parent=self)
            except Exception as e:
                InfoBar.error("오류", f"파일을 저장할 수 없습니다: {e}", duration=4000, parent=self)
                
    def go_to_today(self):
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.showToday()
        self.render_holiday_checks()
        
    def update_calendar_holidays(self):
        year = self.calendar.yearShown()
        holidays = get_korean_holidays(year)
        
        # Apply red color format to Korean holidays
        for date_str, holiday_name in holidays.items():
            y, m, d = map(int, date_str.split('-'))
            qdate = QDate(y, m, d)
            fmt = QTextCharFormat()
            fmt.setForeground(QBrush(QColor("#E81123")))
            fmt.setFontWeight(QFont.Bold)
            fmt.setToolTip(holiday_name)
            self.calendar.setDateTextFormat(qdate, fmt)
            
    def update_calendar_style(self):
        is_dark = isDarkTheme()
        bg_color = "#2C2C2C" if is_dark else "#FFFFFF"
        header_bg = "#202020" if is_dark else "#F9F9F9"
        text_color = "#FFFFFF" if is_dark else "#000000"
        border_color = "#3A3A3A" if is_dark else "#E5E5E5"
        select_bg = "#60CDFF" if is_dark else "#0078D4"
        select_fg = "#000000" if is_dark else "#FFFFFF"
        hover_bg = "#383838" if is_dark else "#EBEBEB"
        pressed_bg = "#4D4D4D" if is_dark else "#D8D8D8"
        disabled_color = "#666666" if is_dark else "#B0B0B0"
        
        # Style today button if it exists
        if hasattr(self, 'today_btn'):
            btn_color = "#60CDFF" if is_dark else "#0078D4"
            btn_hover = "rgba(96, 205, 255, 0.1)" if is_dark else "rgba(0, 120, 212, 0.1)"
            self.today_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {btn_color};
                    font-family: 'SUIT';
                    font-size: 11px;
                    font-weight: bold;
                    border: 1px solid {btn_color};
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    background-color: {btn_hover};
                }}
            """)
        
        # Style navigation buttons directly in code
        from PyQt5.QtWidgets import QToolButton
        from PyQt5.QtGui import QIcon
        
        prev_btn = self.calendar.findChild(QToolButton, "qt_calendar_prevmonth")
        if prev_btn:
            prev_btn.setIcon(QIcon())
            prev_btn.setText("◀")
            
        next_btn = self.calendar.findChild(QToolButton, "qt_calendar_nextmonth")
        if next_btn:
            next_btn.setIcon(QIcon())
            next_btn.setText("▶")
            
        self.calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
            QCalendarWidget QWidget {{
                alternate-background-color: transparent;
                background-color: {bg_color};
                color: {text_color};
                font-family: 'SUIT';
                font-size: 13px;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {header_bg};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border-bottom: 1px solid {border_color};
            }}
            QCalendarWidget QToolButton {{
                color: {text_color};
                background-color: transparent;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                margin: 4px;
                padding: 4px 8px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {hover_bg};
            }}
            QCalendarWidget QToolButton:pressed {{
                background-color: {pressed_bg};
            }}
            QCalendarWidget QMenu {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
            }}
            QCalendarWidget QSpinBox {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                margin-right: 4px;
            }}
            QCalendarWidget QTableView {{
                background-color: {bg_color};
                border: none;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                selection-background-color: {select_bg};
                selection-color: {select_fg};
                gridline-color: transparent;
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {text_color};
            }}
            QCalendarWidget QAbstractItemView:disabled {{
                color: {disabled_color};
            }}
        """)
        
    def update_holiday_panel_style(self):
        is_dark = isDarkTheme()
        border_color = "#3A3A3A" if is_dark else "#E5E5E5"
        bg_color = "#202020" if is_dark else "#FFFFFF"
        self.holiday_list_scroll.setStyleSheet(f"QScrollArea {{ border: 1px solid {border_color}; border-radius: 8px; background-color: {bg_color}; }}")

    def add_company(self):
        dialog = CompanyDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_data()
            self.companies.append(new_data)
            save_companies(self.companies)
            self.render_list()
            InfoBar.success("성공", f"'{new_data['name']}' 업체가 추가되었습니다.", duration=3000, parent=self)
            
    def edit_company(self, index):
        if index < 0 or index >= len(self.companies):
            return
        company_data = self.companies[index]
        dialog = CompanyDialog(company_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_data()
            self.companies[index] = updated_data
            save_companies(self.companies)
            self.render_list()
            InfoBar.success("성공", f"'{updated_data['name']}' 업체 정보가 수정되었습니다.", duration=3000, parent=self)
            
    def delete_company(self, index):
        if index < 0 or index >= len(self.companies):
            return
        company_name = self.companies[index].get('name', '이름 없음')
        
        w = MessageBox('업체 삭제', f"'{company_name}' 업체를 삭제하시겠습니까?", self)
        if w.exec_():
            self.companies.pop(index)
            save_companies(self.companies)
            self.render_list()
            InfoBar.success("성공", f"'{company_name}' 업체가 삭제되었습니다.", duration=3000, parent=self)

