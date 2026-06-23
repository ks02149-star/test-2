from calendar import monthrange

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
from src.ui.components.cards import ScheduleItemWidget
from src.ui.components.dialogs import ScheduleAddDialog
from src.core.schedule_threads import ScheduleAddThread, ScheduleDeleteThread, ScheduleFetchThread
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, FONT_DIR, SETTINGS_PATH, CREDENTIALS_PATH

class ScheduleInterface(ScrollArea):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("ScheduleInterface")
        self.view = QWidget()
        self.view.setObjectName('ScheduleView')
        self.view.setStyleSheet('QWidget#ScheduleView { background-color: transparent; }')
        self.setStyleSheet('QScrollArea { background-color: transparent; border: none; }')
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        
        self.vBoxLayout = QVBoxLayout(self.view)
        self.vBoxLayout.setContentsMargins(30, 30, 30, 30)
        self.vBoxLayout.setSpacing(20)
        
        self.title_label = TitleLabel("월간 일정표")
        self.title_label.setStyleSheet("color: white;")
        self.vBoxLayout.addWidget(self.title_label)
        
        self.control_layout = QHBoxLayout()
        self.year_combo = ComboBox()
        self.month_combo = ComboBox()
        current_date = date.today()
        
        for y in range(current_date.year - 2, current_date.year + 3):
            self.year_combo.addItem(f"{y}년", userData=y)
        for m in range(1, 13):
            self.month_combo.addItem(f"{m}월", userData=m)
            
        self.year_combo.setCurrentIndex(self.year_combo.findData(current_date.year))
        self.month_combo.setCurrentIndex(self.month_combo.findData(current_date.month))
        
        self.year_combo.currentIndexChanged.connect(self.build_calendar)
        self.month_combo.currentIndexChanged.connect(self.build_calendar)
        
        self.refresh_btn = PushButton("수동 새로고침")
        self.refresh_btn.clicked.connect(self.trigger_refresh)
        
        self.today_btn = PushButton("오늘 날짜로")
        self.today_btn.clicked.connect(self.go_to_today)
        
        self.control_layout.addWidget(self.year_combo)
        self.control_layout.addWidget(self.month_combo)
        self.control_layout.addWidget(self.today_btn)
        self.control_layout.addWidget(self.refresh_btn)
        self.control_layout.addStretch(1)
        self.vBoxLayout.addLayout(self.control_layout)
        
        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(1)
        for i in range(7):
            self.calendar_grid.setColumnStretch(i, 1)
        self.vBoxLayout.addLayout(self.calendar_grid)
        self.vBoxLayout.addStretch(1)
        
        self.schedule_data = {}
        self.holidays_data = {}
        
        self.fetch_timer = QTimer(self)
        self.fetch_timer.timeout.connect(self.trigger_refresh)
        self.fetch_timer.start(60000)
        
        self.trigger_refresh()

    def build_calendar(self):
        for i in reversed(range(self.calendar_grid.count())): 
            widget = self.calendar_grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()
                
        year = self.year_combo.currentData()
        month = self.month_combo.currentData()
        if not year or not month: return
        
        days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        for i, day in enumerate(days):
            lbl = QLabel(day)
            lbl.setAlignment(Qt.AlignCenter)
            color = "#ff6b6b" if i == 0 else ("#4dabf7" if i == 6 else "#e0e0e0")
            lbl.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 14px; padding: 5px;")
            self.calendar_grid.addWidget(lbl, 0, i)
            
        first_weekday, num_days = monthrange(year, month)
        first_weekday = (first_weekday + 1) % 7 
        
        row = 1
        col = first_weekday
        
        for d in range(1, num_days + 1):
            date_str = f"{year}-{month:02d}-{d:02d}"
            
            cell_widget = QFrame()
            cell_widget.setMinimumSize(130, 120)
            cell_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
            cell_widget.setFrameShape(QFrame.StyledPanel)
            cell_widget.setStyleSheet("QFrame { background-color: #2b2b2b; border: 1px solid #3c3c3c; border-radius: 4px; } QFrame:hover { background-color: #3b3b3b; }")
            
            cell_layout = QVBoxLayout(cell_widget)
            cell_layout.setContentsMargins(5, 5, 5, 5)
            cell_layout.setSpacing(2)
            
            day_lbl = QLabel(str(d))
            day_color = "#ff6b6b" if col == 0 else ("#4dabf7" if col == 6 else "#e0e0e0")
            
            holiday_text = self.holidays_data.get(date_str)
            if holiday_text:
                day_lbl.setText(f"{d} {holiday_text}")
                day_color = "#ff6b6b"
                
            day_lbl.setStyleSheet(f"color: {day_color}; font-weight: bold; border: none; background: transparent;")
            cell_layout.addWidget(day_lbl)
            
            schedules = self.schedule_data.get(date_str, [])
            for sch_data in schedules:
                if isinstance(sch_data, tuple) and len(sch_data) >= 3:
                    sch, color, creator_id = sch_data[0], sch_data[1], sch_data[2]
                elif isinstance(sch_data, tuple) and len(sch_data) == 2:
                    sch, color = sch_data
                    creator_id = None
                else:
                    sch = sch_data
                    color = "#1976D2"
                    creator_id = None
                
                try:
                    r = int(color[1:3], 16)
                    g = int(color[3:5], 16)
                    b = int(color[5:7], 16)
                    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                    text_color = "#000000" if luminance > 0.5 else "#ffffff"
                except:
                    text_color = "#000000"
                    
                sch_lbl = ScheduleItemWidget(date_str, sch, color, text_color, creator_id)
                sch_lbl.delete_requested.connect(self.delete_schedule)
                cell_layout.addWidget(sch_lbl)
                
            cell_layout.addStretch(1)
            cell_widget.setMinimumHeight(120)
            
            cell_widget.mouseDoubleClickEvent = lambda event, ds=date_str: self.on_cell_double_clicked(ds) if event.button() == Qt.LeftButton else None
            
            self.calendar_grid.addWidget(cell_widget, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1

    def on_cell_double_clicked(self, date_str):
        dialog = ScheduleAddDialog(date_str, self)
        if dialog.exec_():
            start_str, end_str, text = dialog.get_schedule_data()
            if text:
                # Add locally for instant feedback
                from datetime import datetime, timedelta
                start = datetime.strptime(start_str, "%Y-%m-%d")
                end = datetime.strptime(end_str, "%Y-%m-%d")
                current = start
                while current <= end:
                    ds = current.strftime("%Y-%m-%d")
                    if ds not in self.schedule_data:
                        self.schedule_data[ds] = []
                    global SESSION
                    self.schedule_data[ds].append((text, "#1976D2", SESSION.get("id")))
                    current += timedelta(days=1)
                    
                self.build_calendar()
                # Run thread to add to remote
                self.add_thread = ScheduleAddThread(start_str, end_str, text, SESSION.get("id"))
                self.add_thread.error_occurred.connect(self.on_error_occurred)
                self.add_thread.start()

    def delete_schedule(self, date_str, text):
        # Run thread to delete from remote
        global SESSION
        self.del_thread = ScheduleDeleteThread(date_str, text, SESSION.get("id"))
        self.del_thread.error_occurred.connect(lambda err: InfoBar.error("삭제 실패", err, parent=self, position=InfoBarPosition.TOP))
        self.del_thread.success.connect(lambda: InfoBar.success("삭제 성공", "일정이 성공적으로 삭제되었습니다.", parent=self, position=InfoBarPosition.TOP))
        self.del_thread.success.connect(self.trigger_refresh)
        self.del_thread.start()

    def go_to_today(self):
        from datetime import date
        today = date.today()
        y_idx = self.year_combo.findData(today.year)
        m_idx = self.month_combo.findData(today.month)
        if y_idx >= 0: self.year_combo.setCurrentIndex(y_idx)
        if m_idx >= 0: self.month_combo.setCurrentIndex(m_idx)
        self.trigger_refresh()

    def trigger_refresh(self):
        self.fetch_thread = ScheduleFetchThread()
        self.fetch_thread.data_fetched.connect(self.on_data_fetched)
        self.fetch_thread.error_occurred.connect(self.on_error_occurred)
        self.fetch_thread.start()

    def on_data_fetched(self, data):
        self.schedule_data.clear()
        self.holidays_data = data.get('holidays', {})
        for i, row in enumerate(data.get('schedules', [])):
            if len(row) < 3 or row[0].strip() == '날짜' or row[0].strip() == 'Date': continue
            d_str = row[0].strip()
            sch = row[1].strip()
            color = row[2]
            creator_id = row[3] if len(row) >= 4 else ""
            if d_str and sch:
                if d_str not in self.schedule_data:
                    self.schedule_data[d_str] = []
                self.schedule_data[d_str].append((sch, color, creator_id))
        self.build_calendar()
        
        if self.main_window and hasattr(self.main_window, 'home_interface'):
            # 홈 화면에도 새 스케줄 데이터를 전달하여 실시간 동기화
            self.main_window.home_interface.on_schedule_fetched(data)

    def on_error_occurred(self, err):
        pass

