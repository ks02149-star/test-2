import os
from datetime import datetime, date
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QGridLayout, QButtonGroup
from PyQt5.QtGui import QFont
from qfluentwidgets import (ScrollArea, CardWidget, ComboBox, LineEdit, TextEdit, 
                            PrimaryPushButton, CalendarPicker, TitleLabel, SubtitleLabel, InfoBar, InfoBarPosition, BodyLabel, CheckBox)
from src.config import SESSION, APPROVAL_SPREADSHEET_ID, TEMPLATE_LEAVE_REQUEST_ID, SPREADSHEET_ID
from src.core.google_sheets_manager import GoogleSheetsManager
from src.ui.components.calendar_widget import ScheduleCalendarWidget

class ScheduleFetchWorker(QThread):
    finished = pyqtSignal(bool, dict, dict, str)
    
    def run(self):
        try:
            manager = GoogleSheetsManager()
            
            def _fetch():
                client = manager.get_client()
                url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?includeGridData=true&ranges=schedule!A:C&ranges=holidays!A:B'
                return client.http_client.request('get', url)
            
            res = manager.execute_with_retry(_fetch)
            if res.status_code != 200:
                raise Exception("데이터를 가져오는데 실패했습니다.")
                
            sheets = res.json().get('sheets', [])
            
            schedule_grid = []
            holidays_grid = []
            for sheet in sheets:
                title = sheet.get('properties', {}).get('title', '')
                grid_data = sheet.get('data', [{}])[0].get('rowData', [])
                if title == 'schedule':
                    schedule_grid = grid_data
                elif title == 'holidays':
                    holidays_grid = grid_data
            
            schedule_data = {}
            for row in schedule_grid:
                if 'values' in row and len(row['values']) >= 2:
                    date_val = row['values'][0].get('formattedValue', '')
                    text_val = row['values'][1].get('formattedValue', '')
                    
                    if not date_val or not text_val:
                        continue
                    
                    # 필터링 로직: [연차], [오전반차], [오후반차] 가 포함된 것만
                    if "[연차]" in text_val or "[휴가]" in text_val or "[오전반차]" in text_val or "[오후반차]" in text_val:
                        color_data = row['values'][1].get('effectiveFormat', {}).get('backgroundColor', {})
                        r = int(color_data.get('red', 1) * 255)
                        g = int(color_data.get('green', 1) * 255)
                        b = int(color_data.get('blue', 1) * 255)
                        color_hex = f'#{r:02x}{g:02x}{b:02x}'
                        
                        if color_hex.lower() == '#ffffff':
                            if '김현우' in text_val or '공훈식' in text_val:
                                color_hex = '#c9daf8'
                            elif '김태훈' in text_val or '장여진' in text_val:
                                color_hex = '#d9d2e9'
                            elif text_val.strip():
                                color_hex = '#d9ead3'
                            else:
                                color_hex = '#ffffff'
                                
                        if date_val not in schedule_data:
                            schedule_data[date_val] = []
                        schedule_data[date_val].append((text_val, color_hex))
                        
            # 공휴일 데이터 가져오기
            holidays_data = {}
            import re
            for row in holidays_grid:
                if 'values' in row and len(row['values']) >= 2:
                    date_val = row['values'][0].get('formattedValue', '')
                    text_val = row['values'][1].get('formattedValue', '')
                    if date_val and text_val:
                        match = re.search(r'(\d{4}-\d{2}-\d{2})', date_val)
                        if match:
                            parsed_date = match.group(1)
                            if parsed_date not in holidays_data:
                                holidays_data[parsed_date] = text_val
                        
            self.finished.emit(True, schedule_data, holidays_data, "")
        except Exception as e:
            self.finished.emit(False, {}, {}, str(e))

class ApprovalRequestWorker(QThread):
    finished = pyqtSignal(bool, str)
    
    def __init__(self, data):
        super().__init__()
        self.data = data
        
    def run(self):
        try:
            manager = GoogleSheetsManager()
            
            from src.config import SESSION, APPROVAL_SPREADSHEET_ID, TEMPLATE_LEAVE_REQUEST_ID, ROOT_LEAVE_HISTORY_FOLDER_ID
            
            today = datetime.now()
            s_date = self.data['start_date']
            e_date = self.data['end_date']
            days_str = self.data['days_str']
            half_day_type = self.data.get('half_day_type', '')
            
            period_str = f"{s_date.strftime('%Y-%m-%d')} ~ {e_date.strftime('%Y-%m-%d')}"
            
            # 반차일 경우 포맷팅
            period_days_str = f"{days_str}일간"
            if half_day_type == "AM":
                period_days_str = f"{days_str}일간 (오전)"
            elif half_day_type == "PM":
                period_days_str = f"{days_str}일간 (오후)"
                
            req_date_str = today.strftime("%Y-%m-%d")
            
            payload = {
                'action': 'request',
                'templateId': TEMPLATE_LEAVE_REQUEST_ID,
                'rawSpreadsheetId': APPROVAL_SPREADSHEET_ID,
                'rootFolderId': ROOT_LEAVE_HISTORY_FOLDER_ID,
                'requester': self.data['requester'],
                'docType': self.data['doc_type'],
                'position': self.data['position'],
                'reason': self.data['reason'],
                'sDateY': s_date.year, 'sDateM': s_date.month, 'sDateD': s_date.day,
                'eDateY': e_date.year, 'eDateM': e_date.month, 'eDateD': e_date.day,
                'daysStr': days_str, # GAS 양식에는 순수 숫자만
                'periodStr': period_str,
                'periodDaysStr': period_days_str, # RAW DATA 에는 괄호 포함
                'reqDateStr': req_date_str,
                'todayY': s_date.year, 'todayM': s_date.month, 'todayD': today.day,
                'yearStr': f"{s_date.year}년",
                'monthStr': f"{s_date.month:02d}월",
                'fileName': f"{today.strftime('%y%m%d')}_{self.data['requester']}_{self.data['doc_type']}"
            }
            
            # 사전에 연도 및 월 폴더를 생성하여 폴더 누락으로 인한 에러를 방지합니다.
            year_str = f"{s_date.year}년"
            month_str = f"{s_date.month:02d}월"
            year_folder_id = manager.get_or_create_folder(year_str, ROOT_LEAVE_HISTORY_FOLDER_ID)
            manager.get_or_create_folder(month_str, year_folder_id)
            
            manager.request_approval_via_gas(payload)
            
            self.finished.emit(True, "결재 요청이 성공적으로 완료되었습니다.")
        except Exception as e:
            import gspread
            if isinstance(e, gspread.exceptions.SpreadsheetNotFound) or "<Response [404]>" in str(e):
                error_msg = "원본 양식(연차휴가신청서) 파일에 접근할 수 없습니다!\n해당 파일의 공유 버튼을 눌러 '링크가 있는 모든 사용자(편집자)'로 권한을 변경해주세요."
                self.finished.emit(False, error_msg)
            else:
                self.finished.emit(False, f"결재 요청 중 오류가 발생했습니다: {str(e)}")

class ApprovalRequestInterface(ScrollArea):
    def __init__(self, main_window, parent=None):
        super().__init__(parent=parent)
        self.main_window = main_window
        self.setObjectName("ApprovalRequestInterface")
        
        self.view = QWidget(self)
        self.view.setObjectName('ApprovalRequestView')
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.view.setStyleSheet("QWidget#ApprovalRequestView { background-color: transparent; }")
        
        self.vbox = QVBoxLayout(self.view)
        self.vbox.setContentsMargins(40, 40, 40, 40)
        self.vbox.setSpacing(20)
        
        # 헤더
        title = TitleLabel("전자결재 기안")
        title.setFont(QFont("SUIT", 24, QFont.Bold))
        self.vbox.addWidget(title)
        
        subtitle = SubtitleLabel("새로운 결재 서류를 작성하고 요청합니다.")
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        self.vbox.addWidget(subtitle)
        
        # 메인 좌우 분할
        self.main_hlayout = QHBoxLayout()
        self.main_hlayout.setSpacing(20)
        
        # ----------------------------------------------------
        # 좌측: 기안 폼 영역
        # ----------------------------------------------------
        self.form_card = CardWidget(self)
        self.form_layout = QVBoxLayout(self.form_card)
        self.form_layout.setContentsMargins(30, 30, 30, 30)
        self.form_layout.setSpacing(20)
        
        # Row 1 (Grid)
        row1_layout = QHBoxLayout()
        
        v1 = QVBoxLayout()
        v1.addWidget(BodyLabel("결재 서류 종류"))
        self.doc_combo = ComboBox()
        self.doc_combo.addItem("연차휴가신청서")
        v1.addWidget(self.doc_combo)
        row1_layout.addLayout(v1, 2)
        
        v2 = QVBoxLayout()
        v2.addWidget(BodyLabel("기안자 (결재 요청자)"))
        self.requester_edit = LineEdit()
        self.requester_edit.setText(SESSION.get('name', ''))
        self.requester_edit.setReadOnly(True)
        v2.addWidget(self.requester_edit)
        row1_layout.addLayout(v2, 1)
        
        v3 = QVBoxLayout()
        v3.addWidget(BodyLabel("직책"))
        self.position_edit = LineEdit()
        self.position_edit.setPlaceholderText("직책을 입력하세요 (예: 사원)")
        v3.addWidget(self.position_edit)
        row1_layout.addLayout(v3, 1)
        
        self.form_layout.addLayout(row1_layout)
        
        # Row 2 (Grid)
        row2_layout = QHBoxLayout()
        
        sv1 = QVBoxLayout()
        sv1.addWidget(BodyLabel("시작 날짜"))
        self.start_date_picker = CalendarPicker()
        sv1.addWidget(self.start_date_picker)
        row2_layout.addLayout(sv1, 2)
        
        sv2 = QVBoxLayout()
        sv2.addWidget(BodyLabel("종료 날짜"))
        self.end_date_picker = CalendarPicker()
        sv2.addWidget(self.end_date_picker)
        row2_layout.addLayout(sv2, 2)
        
        sv3 = QVBoxLayout()
        sv3.addWidget(BodyLabel("일수 (예: 1, 0.5)"))
        self.days_edit = LineEdit()
        self.days_edit.setPlaceholderText("사용 일수")
        self.days_edit.setFixedWidth(80)
        self.days_edit.textChanged.connect(self.on_days_changed)
        sv3.addWidget(self.days_edit)
        row2_layout.addLayout(sv3, 2)
        
        # 반차 체크박스 영역
        checkbox_vbox = QVBoxLayout()
        checkbox_vbox.setSpacing(5)
        
        self.am_checkbox = CheckBox("오전반차")
        self.pm_checkbox = CheckBox("오후반차")
        self.am_checkbox.setEnabled(False)
        self.pm_checkbox.setEnabled(False)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self.btn_group.addButton(self.am_checkbox)
        self.btn_group.addButton(self.pm_checkbox)
        
        checkbox_vbox.addWidget(self.am_checkbox)
        checkbox_vbox.addWidget(self.pm_checkbox)
        row2_layout.addLayout(checkbox_vbox, 1)
        
        self.form_layout.addLayout(row2_layout)
        
        # Row 3 (사유)
        self.form_layout.addWidget(BodyLabel("사유"))
        self.reason_edit = TextEdit()
        self.reason_edit.setPlaceholderText("신청 사유를 상세히 적어주세요.")
        self.reason_edit.setFixedHeight(120)
        self.form_layout.addWidget(self.reason_edit)
        
        # Row 4 (버튼)
        self.submit_btn = PrimaryPushButton("결재 요청하기")
        self.submit_btn.clicked.connect(self.on_submit)
        self.form_layout.addWidget(self.submit_btn, alignment=Qt.AlignRight)
        
        self.main_hlayout.addWidget(self.form_card, 5, Qt.AlignTop) # 5 비율, 상단 정렬
        
        # ----------------------------------------------------
        # 우측: 캘린더 위젯
        # ----------------------------------------------------
        self.cal_layout = QVBoxLayout()
        self.cal_control_layout = QHBoxLayout()
        
        self.year_combo = ComboBox()
        self.month_combo = ComboBox()
        current_date = date.today()
        
        for y in range(current_date.year - 2, current_date.year + 3):
            self.year_combo.addItem(f"{y}년", userData=y)
        for m in range(1, 13):
            self.month_combo.addItem(f"{m}월", userData=m)
            
        self.year_combo.setCurrentIndex(self.year_combo.findData(current_date.year))
        self.month_combo.setCurrentIndex(self.month_combo.findData(current_date.month))
        
        self.year_combo.currentIndexChanged.connect(self.on_month_changed)
        self.month_combo.currentIndexChanged.connect(self.on_month_changed)
        
        self.cal_control_layout.addStretch(1)
        self.cal_control_layout.addWidget(self.year_combo)
        self.cal_control_layout.addWidget(self.month_combo)
        
        self.cal_layout.addLayout(self.cal_control_layout)
        
        self.calendar_widget = ScheduleCalendarWidget(self)
        self.cal_layout.addWidget(self.calendar_widget)
        
        self.main_hlayout.addLayout(self.cal_layout, 5) # 5 비율
        
        self.vbox.addLayout(self.main_hlayout)
        self.vbox.addStretch(1)
        
        self.worker = None
        self.fetch_worker = None
        self.schedule_data = {}
        self.holidays_data = {}
        
        # 캘린더 초기 로드
        self.load_calendar_data()
        
    def on_days_changed(self, text):
        if text.strip() == "0.5":
            self.am_checkbox.setEnabled(True)
            self.pm_checkbox.setEnabled(True)
        else:
            self.btn_group.setExclusive(False)
            self.am_checkbox.setChecked(False)
            self.pm_checkbox.setChecked(False)
            self.btn_group.setExclusive(True)
            self.am_checkbox.setEnabled(False)
            self.pm_checkbox.setEnabled(False)
            
    def showEvent(self, event):
        super().showEvent(event)
        self.load_calendar_data()
        
    def load_calendar_data(self):
        self.fetch_worker = ScheduleFetchWorker()
        self.fetch_worker.finished.connect(self.on_calendar_data_loaded)
        self.fetch_worker.start()
        
    def on_calendar_data_loaded(self, success, schedule_data, holidays_data, error_msg):
        if success:
            self.schedule_data = schedule_data
            self.holidays_data = holidays_data
            self.on_month_changed()
        else:
            print(f"캘린더 데이터 로드 실패: {error_msg}")
            
    def on_month_changed(self):
        y = self.year_combo.currentData()
        m = self.month_combo.currentData()
        if y and m:
            self.calendar_widget.update_calendar(y, m, self.schedule_data, self.holidays_data)
        
    def on_submit(self):
        doc_type = self.doc_combo.text()
        position = self.position_edit.text().strip()
        reason = self.reason_edit.toPlainText().strip()
        days_str = self.days_edit.text().strip()
        start_qdate = self.start_date_picker.getDate()
        end_qdate = self.end_date_picker.getDate()
        
        if not position:
            InfoBar.error("오류", "직책을 입력해주세요.", duration=2000, parent=self)
            return
        if not reason:
            InfoBar.error("오류", "사유를 입력해주세요.", duration=2000, parent=self)
            return
        if not days_str:
            InfoBar.error("오류", "일수를 입력해주세요. (예: 1, 0.5)", duration=2000, parent=self)
            return
            
        try:
            days_float = float(days_str)
            if days_float <= 0:
                raise ValueError
        except ValueError:
            InfoBar.error("오류", "일수는 0보다 큰 숫자여야 합니다.", duration=2000, parent=self)
            return
            
        start_date = date(start_qdate.year(), start_qdate.month(), start_qdate.day())
        end_date = date(end_qdate.year(), end_qdate.month(), end_qdate.day())
        
        if start_date > end_date:
            InfoBar.error("오류", "종료 날짜가 시작 날짜보다 빠를 수 없습니다.", duration=2000, parent=self)
            return
            
        half_day_type = ""
        if days_str == "0.5":
            if self.am_checkbox.isChecked():
                half_day_type = "AM"
            elif self.pm_checkbox.isChecked():
                half_day_type = "PM"
            else:
                InfoBar.error("오류", "오전/오후 반차 중 하나를 선택해주세요.", duration=2000, parent=self)
                return
            
        data = {
            'doc_type': doc_type,
            'requester': SESSION.get('name', ''),
            'position': position,
            'reason': reason,
            'days_str': days_str,
            'half_day_type': half_day_type,
            'start_date': start_date,
            'end_date': end_date
        }
        
        self.submit_btn.setEnabled(False)
        self.submit_btn.setText("요청 처리 중...")
        
        self.worker = ApprovalRequestWorker(data)
        self.worker.finished.connect(self.on_submit_finished)
        self.worker.start()
        
    def on_submit_finished(self, success, message):
        self.submit_btn.setEnabled(True)
        self.submit_btn.setText("결재 요청하기")
        
        if success:
            InfoBar.success("성공", message, duration=3000, parent=self)
            self.position_edit.clear()
            self.reason_edit.clear()
        else:
            InfoBar.error("실패", message, duration=5000, parent=self)
