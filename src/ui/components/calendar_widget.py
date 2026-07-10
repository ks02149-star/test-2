import calendar
from datetime import datetime
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QFrame, QLabel, QSizePolicy
from PyQt5.QtGui import QColor, QFont
from qfluentwidgets import CardWidget, ScrollArea

class ScheduleCalendarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        
        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(1)
        for i in range(7):
            self.calendar_grid.setColumnStretch(i, 1)
            
        self.layout.addLayout(self.calendar_grid)
        self.layout.addStretch(1)
        
    def update_calendar(self, year, month, schedule_data, holidays_data=None):
        if holidays_data is None:
            holidays_data = {}
            
        # 기존 그리드 내용 지우기
        for i in reversed(range(self.calendar_grid.count())): 
            widget = self.calendar_grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()
                
        # 요일 헤더 렌더링
        days = ["일", "월", "화", "수", "목", "금", "토"]
        for i, day in enumerate(days):
            lbl = QLabel(day)
            lbl.setAlignment(Qt.AlignCenter)
            color = "#ff6b6b" if i == 0 else ("#4dabf7" if i == 6 else "#e0e0e0")
            lbl.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 14px; padding: 5px;")
            self.calendar_grid.addWidget(lbl, 0, i)
            
        cal = calendar.Calendar(firstweekday=6) # 일요일부터 시작
        month_days = cal.monthdatescalendar(year, month)
        
        row = 1
        for week in month_days:
            for col, current_date in enumerate(week):
                date_str = current_date.strftime("%Y-%m-%d")
                is_current_month = (current_date.month == month)
                
                cell_widget = QFrame()
                cell_widget.setMinimumSize(40, 60)
                cell_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
                cell_widget.setFrameShape(QFrame.StyledPanel)
                
                # 월간 스케줄과 동일한 QFrame 다크 테마 스타일
                bg_color = "#2b2b2b" if is_current_month else "#1e1e1e"
                border_color = "#3c3c3c" if is_current_month else "#2a2a2a"
                hover_color = "#3b3b3b" if is_current_month else "#2b2b2b"
                
                cell_widget.setStyleSheet(f"QFrame {{ background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 4px; }} QFrame:hover {{ background-color: {hover_color}; }}")
                
                cell_layout = QVBoxLayout(cell_widget)
                cell_layout.setContentsMargins(5, 5, 5, 5)
                cell_layout.setSpacing(2)
                
                # 날짜 및 공휴일 표시
                day_lbl = QLabel(str(current_date.day))
                day_color = "#ff6b6b" if col == 0 else ("#4dabf7" if col == 6 else "#e0e0e0")
                if not is_current_month:
                    day_color = "gray"
                
                holiday_text = holidays_data.get(date_str)
                if holiday_text:
                    day_lbl.setText(f"{current_date.day} {holiday_text}")
                    day_color = "#ff6b6b"
                    
                day_lbl.setStyleSheet(f"color: {day_color}; font-weight: bold; border: none; background: transparent;")
                cell_layout.addWidget(day_lbl)
                
                # 스케줄 렌더링
                schedules = schedule_data.get(date_str, [])
                for sch_item in schedules:
                    if isinstance(sch_item, tuple):
                        schedule_text, chip_bg = sch_item
                    else:
                        schedule_text = sch_item
                        # Fallback just in case
                        chip_bg = "rgba(180, 200, 255, 0.8)"
                        if "[연차]" in schedule_text or "[휴가]" in schedule_text:
                            chip_bg = "rgba(220, 200, 255, 0.8)"
                        elif "[오후반차]" in schedule_text:
                            chip_bg = "rgba(200, 230, 200, 0.8)"
                        elif "[오전반차]" in schedule_text:
                            chip_bg = "rgba(200, 200, 230, 0.8)"
                            
                    chip = QLabel(schedule_text)
                    chip.setFont(QFont("SUIT", 8))
                    
                    # 텍스트 컬러 계산
                    try:
                        if chip_bg.startswith('#') and len(chip_bg) == 7:
                            r = int(chip_bg[1:3], 16)
                            g = int(chip_bg[3:5], 16)
                            b = int(chip_bg[5:7], 16)
                            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                            text_color = "#000000" if luminance > 0.5 else "#ffffff"
                        else:
                            text_color = "black"
                    except:
                        text_color = "black"
                        
                    chip.setStyleSheet(f"background-color: {chip_bg}; color: {text_color}; border-radius: 3px; padding: 2px; border: none;")
                    chip.setWordWrap(False)
                    cell_layout.addWidget(chip)
                    
                cell_layout.addStretch(1)
                cell_widget.setMinimumHeight(100)
                
                self.calendar_grid.addWidget(cell_widget, row, col)
            row += 1
