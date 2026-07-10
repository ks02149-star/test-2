import os
from datetime import datetime
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QHeaderView, QTableWidgetItem, QMessageBox, QPushButton
from PyQt5.QtGui import QFont, QColor
from qfluentwidgets import (ScrollArea, CardWidget, TableWidget, PrimaryPushButton, 
                            TitleLabel, SubtitleLabel, InfoBar, PushButton)
from src.config import SESSION, APPROVAL_SPREADSHEET_ID, APPROVAL_IMAGE_FOLDER_ID
from src.core.google_sheets_manager import GoogleSheetsManager

class ApprovalManageFetchWorker(QThread):
    finished = pyqtSignal(bool, list, str)
    
    def run(self):
        try:
            manager = GoogleSheetsManager()
            ws_raw = manager.get_worksheet(APPROVAL_SPREADSHEET_ID, "전자결재 RAW DATA")
            all_records = ws_raw.get_all_values()
            
            if len(all_records) <= 4:
                self.finished.emit(True, [], "")
                return
                
            pending_records = []
            for idx, row in enumerate(all_records[4:]):
                if not row or not row[0]:
                    continue
                while len(row) < 11:
                    row.append("")
                # I열(인덱스 8)이 공란인 것만 (대기중)
                if row[8].strip() == "":
                    # 저장할 때 실제 시트의 row 번호 (4를 더하고 1-indexed이므로 +1 -> idx + 5)
                    row_idx = idx + 5
                    pending_records.append((row_idx, row))
            
            pending_records.reverse()
            self.finished.emit(True, pending_records, "")
            
        except Exception as e:
            self.finished.emit(False, [], str(e))

class ApprovalManageProcessWorker(QThread):
    finished = pyqtSignal(bool, str)
    
    def __init__(self, action, records_to_process):
        super().__init__()
        self.action = action # "Y" or "N"
        self.records_to_process = records_to_process
        
    def run(self):
        try:
            manager = GoogleSheetsManager()
            
            ws_raw = manager.get_worksheet(APPROVAL_SPREADSHEET_ID, "전자결재 RAW DATA")
            admin_name = SESSION.get('name', '관리자')
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            image_name = "승인" if self.action == "Y" else "반려"
            img_file_id = manager.search_drive_file(image_name, APPROVAL_IMAGE_FOLDER_ID, contains=True)
            img_url = manager.get_file_web_content_link(img_file_id) if img_file_id else None
            
            from src.config import SPREADSHEET_ID
            from datetime import timedelta
            
            schedule_ws = None
            if self.action == "Y":
                schedule_ws = manager.get_worksheet(SPREADSHEET_ID, "schedule")
            
            for row_idx, record in self.records_to_process:
                # 1. 시트 업데이트
                # H: 승인자(8), I: 승인여부(9), J: 승인날짜(10)
                ws_raw.update(f"H{row_idx}:J{row_idx}", [[admin_name, self.action, today_str]])
                
                # 2. 승인 이미지 스탬프
                file_id = record[10].strip() if len(record) > 10 else ""
                if file_id:
                    if img_url:
                        # IMAGE 함수 구문으로 GAS에 호출하여 해당 파일에 이미지(CellImage)를 삽입 (앱스크립트 스크립트 실행)
                        manager.stamp_document_via_gas(file_id, img_url)
                        
                    # 반려일 경우 파일 이름을 앞에 [반려] 붙이기
                    if self.action == "N":
                        manager.rename_and_move_file(file_id, new_name=f"[반려] {record[0]} - {record[1]}")
                        
                # 3. 스케줄 자동 연동 (승인 & 연차휴가신청서)
                if self.action == "Y" and record[1] == "연차휴가신청서" and schedule_ws:
                    creator_name = record[0].strip()
                    period = record[4].strip() # e.g. "0.5일간 (오전)"
                    period_date = record[5].strip() # e.g. "2026-07-22 ~ 2026-07-25" or "2026-07-22"
                    
                    if "(오전)" in period:
                        prefix = "[오전반차]"
                    elif "(오후)" in period:
                        prefix = "[오후반차]"
                    else:
                        prefix = "[연차]"
                        
                    schedule_text = f"{prefix} {creator_name}"
                    
                    dates = [d.strip() for d in period_date.split('~')]
                    start_str = dates[0]
                    end_str = dates[1] if len(dates) > 1 else start_str
                    
                    try:
                        start_date = datetime.strptime(start_str, "%Y-%m-%d")
                        end_date = datetime.strptime(end_str, "%Y-%m-%d")
                        
                        rows_to_add = []
                        current = start_date
                        while current <= end_date:
                            rows_to_add.append([current.strftime("%Y-%m-%d"), schedule_text, creator_name])
                            current += timedelta(days=1)
                            
                        if len(rows_to_add) > 1:
                            schedule_ws.append_rows(rows_to_add)
                        elif len(rows_to_add) == 1:
                            schedule_ws.append_row(rows_to_add[0])
                    except Exception as date_e:
                        print(f"스케줄 연동 중 날짜 파싱 오류: {date_e}")
            
            msg = "결재 처리가 완료되었습니다." if len(self.records_to_process) == 1 else f"총 {len(self.records_to_process)}건의 결재 처리가 완료되었습니다."
            self.finished.emit(True, msg)
        except Exception as e:
            self.finished.emit(False, f"결재 처리 중 오류가 발생했습니다: {str(e)}")

class ApprovalManageInterface(ScrollArea):
    def __init__(self, main_window, parent=None):
        super().__init__(parent=parent)
        self.main_window = main_window
        self.setObjectName("ApprovalManageInterface")
        
        self.view = QWidget(self)
        self.view.setObjectName('ApprovalManageView')
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.view.setStyleSheet("QWidget#ApprovalManageView { background-color: transparent; }")
        
        self.vbox = QVBoxLayout(self.view)
        self.vbox.setContentsMargins(40, 40, 40, 40)
        self.vbox.setSpacing(20)
        
        # 헤더 영역
        header_layout = QHBoxLayout()
        title_vbox = QVBoxLayout()
        
        title = TitleLabel("결재관리")
        title.setFont(QFont("SUIT", 24, QFont.Bold))
        title_vbox.addWidget(title)
        
        subtitle = SubtitleLabel("사원들이 올린 결재를 확인하고 승인/반려 처리합니다.")
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        title_vbox.addWidget(subtitle)
        
        header_layout.addLayout(title_vbox)
        header_layout.addStretch(1)
        
        self.btn_approve_all = PrimaryPushButton("모두 승인")
        self.btn_approve_all.setFixedSize(90, 32)
        self.btn_approve_all.clicked.connect(lambda: self.process_all_approval("Y"))
        
        self.btn_reject_all = PushButton("모두 반려")
        self.btn_reject_all.setFixedSize(90, 32)
        self.btn_reject_all.clicked.connect(lambda: self.process_all_approval("N"))
        self.btn_reject_all.setStyleSheet("""
            PushButton {
                background-color: #E67E22;
                color: white;
                border: none;
                border-radius: 5px;
            }
            PushButton:hover { background-color: #D35400; }
            PushButton:pressed { background-color: #A04000; }
        """)

        self.refresh_btn = PushButton("새로고침")
        self.refresh_btn.setFixedSize(90, 32)
        self.refresh_btn.clicked.connect(self.load_data)
        self.refresh_btn.setStyleSheet("""
            PushButton {
                background-color: #555555;
                color: white;
                border: none;
                border-radius: 5px;
            }
            PushButton:hover { background-color: #444444; }
            PushButton:pressed { background-color: #333333; }
        """)
        
        header_layout.addWidget(self.btn_approve_all, alignment=Qt.AlignBottom)
        header_layout.addWidget(self.btn_reject_all, alignment=Qt.AlignBottom)
        header_layout.addWidget(self.refresh_btn, alignment=Qt.AlignBottom)
        
        self.vbox.addLayout(header_layout)
        
        # 테이블
        self.card = CardWidget(self)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(20, 20, 20, 20)
        
        self.table = TableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["기안자", "결재종류", "요청일자", "사유", "기간 날짜", "기간", "액션"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.card_layout.addWidget(self.table)
        self.vbox.addWidget(self.card)
        
        self.vbox.addStretch(1)
        
        self.fetch_worker = None
        self.process_worker = None
        self.current_records = []
        self.is_silent = False
        
        # 10초 자동 새로고침 타이머 설정
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.auto_load_data)
        self.refresh_timer.start(10000) # 10초
        
    def auto_load_data(self):
        # 만약 진행 중인 결재가 있다면 새로고침 스킵 (버튼 클릭 방해 방지)
        if self.process_worker and self.process_worker.isRunning():
            return
        self.load_data(silent=True)
        
    def load_data(self, silent=False):
        self.is_silent = silent
        if not self.is_silent:
            self.refresh_btn.setEnabled(False)
            self.btn_approve_all.setEnabled(False)
            self.btn_reject_all.setEnabled(False)
            self.refresh_btn.setText("로딩 중...")
            self.table.setRowCount(0)
        
        self.fetch_worker = ApprovalManageFetchWorker()
        self.fetch_worker.finished.connect(self.on_data_loaded)
        self.fetch_worker.start()
        
    def on_data_loaded(self, success, records, error_msg):
        if not self.is_silent:
            self.refresh_btn.setEnabled(True)
            self.btn_approve_all.setEnabled(True)
            self.btn_reject_all.setEnabled(True)
            self.refresh_btn.setText("새로고침")
        
        if not success:
            if not self.is_silent:
                InfoBar.error("불러오기 실패", error_msg, duration=5000, parent=self)
            return
            
        self.current_records = records
        self.table.setRowCount(len(records))
        for i, (row_idx, row) in enumerate(records):
            requester = row[0]
            doc_type = row[1]
            reason = row[3]
            period = row[4]
            period_date = row[5] # 기간 날짜
            req_date = row[6]
            
            items = [
                QTableWidgetItem(requester),
                QTableWidgetItem(doc_type),
                QTableWidgetItem(req_date),
                QTableWidgetItem(reason),
                QTableWidgetItem(period_date),
                QTableWidgetItem(period)
            ]
            
            for j, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemIsEditable) # Read-only
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, j, item)
                
            # 액션 위젯
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 5, 5, 5)
            
            btn_approve = PrimaryPushButton("승인")
            btn_approve.setFixedSize(60, 32)
            btn_approve.clicked.connect(lambda checked, idx=i: self.process_approval("Y", idx))
            
            btn_reject = PushButton("반려")
            btn_reject.setFixedSize(60, 32)
            btn_reject.clicked.connect(lambda checked, idx=i: self.process_approval("N", idx))
            btn_reject.setStyleSheet("""
                PushButton {
                    background-color: #E67E22;
                    color: white;
                    border: none;
                    border-radius: 5px;
                }
                PushButton:hover { background-color: #D35400; }
                PushButton:pressed { background-color: #A04000; }
            """)
            
            action_layout.addWidget(btn_approve)
            action_layout.addWidget(btn_reject)
            
            self.table.setCellWidget(i, 6, action_widget)
            
    def process_approval(self, action, list_idx):
        if self.process_worker and self.process_worker.isRunning():
            InfoBar.warning("경고", "다른 결재가 처리 중입니다.", duration=2000, parent=self)
            return
            
        row_idx, record = self.current_records[list_idx]
        action_text = "승인" if action == "Y" else "반려"
        
        reply = QMessageBox.question(self, '확인', f"{record[0]}님의 {record[1]}를 {action_text}하시겠습니까?", 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 테이블 비활성화
            self.table.setEnabled(False)
            self.btn_approve_all.setEnabled(False)
            self.btn_reject_all.setEnabled(False)
            
            self.process_worker = ApprovalManageProcessWorker(action, [(row_idx, record)])
            self.process_worker.finished.connect(self.on_process_finished)
            self.process_worker.start()

    def process_all_approval(self, action):
        if not self.current_records:
            InfoBar.warning("알림", "처리할 결재 대기 건이 없습니다.", duration=2000, parent=self)
            return
            
        if self.process_worker and self.process_worker.isRunning():
            InfoBar.warning("경고", "다른 결재가 처리 중입니다.", duration=2000, parent=self)
            return
            
        action_text = "승인" if action == "Y" else "반려"
        count = len(self.current_records)
        
        reply = QMessageBox.question(self, '확인', f"대기 중인 {count}건의 결재를 모두 {action_text}하시겠습니까?", 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.table.setEnabled(False)
            self.btn_approve_all.setEnabled(False)
            self.btn_reject_all.setEnabled(False)
            
            self.process_worker = ApprovalManageProcessWorker(action, self.current_records)
            self.process_worker.finished.connect(self.on_process_finished)
            self.process_worker.start()
            
    def on_process_finished(self, success, message):
        self.table.setEnabled(True)
        self.btn_approve_all.setEnabled(True)
        self.btn_reject_all.setEnabled(True)
        if success:
            InfoBar.success("처리 완료", message, duration=3000, parent=self)
            self.load_data() # 재로딩
        else:
            InfoBar.error("처리 실패", message, duration=5000, parent=self)
