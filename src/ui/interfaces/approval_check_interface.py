import os
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QHeaderView, QTableWidgetItem
from PyQt5.QtGui import QFont, QColor
import requests
from qfluentwidgets import (ScrollArea, CardWidget, TableWidget, PrimaryPushButton, 
                            TitleLabel, SubtitleLabel, InfoBar)
from PyQt5.QtWidgets import QMenu, QAction, QMessageBox
from src.config import SESSION, APPROVAL_SPREADSHEET_ID
from src.core.google_sheets_manager import GoogleSheetsManager

class ApprovalCheckWorker(QThread):
    finished = pyqtSignal(bool, list, str)
    
    def run(self):
        try:
            manager = GoogleSheetsManager()
            ws_raw = manager.get_worksheet(APPROVAL_SPREADSHEET_ID, "전자결재 RAW DATA")
            all_records = ws_raw.get_all_values()
            
            # 1행~4행은 헤더 등 제외, 5행부터 데이터 (인덱스는 4부터)
            if len(all_records) <= 4:
                self.finished.emit(True, [], "")
                return
                
            my_records = []
            for idx, row in enumerate(all_records[4:]):
                row_idx = idx + 5 # 1-based index in google sheets
                if not row or not row[0]:
                    continue
                # A열(인덱스 0)이 내 이름인 것만
                if row[0].strip() == SESSION.get('name', ''):
                    # 구조: A(결재요청자), B(결재종류), C(직책), D(사유), E(기간), F(기간날짜), G(결재요청날짜), H(결재승인자), I(승인여부), J(승인날짜)
                    # 모자란 길이는 공백으로 패딩 (파일 ID인 11번째 열까지)
                    while len(row) < 11:
                        row.append("")
                    file_id = row[10].strip()
                    my_records.append({"row_idx": row_idx, "file_id": file_id, "data": row})
            
            # 최신 순(아래에 추가되므로 역순)으로 정렬
            my_records.reverse()
            self.finished.emit(True, my_records, "")
            
        except Exception as e:
            self.finished.emit(False, [], str(e))

class ApprovalCancelWorker(QThread):
    finished = pyqtSignal(bool, str)
    
    def __init__(self, row_idx, file_id=""):
        super().__init__()
        self.row_idx = row_idx
        self.file_id = file_id
        
    def run(self):
        try:
            manager = GoogleSheetsManager()
            
            # 구글 드라이브 파일 삭제 (파일 ID가 있는 경우)
            if self.file_id:
                def _remove_file():
                    headers = manager._get_drive_headers()
                    # 1. 파일 정보(부모 폴더 및 이름) 가져오기
                    res_get = requests.get(f"https://www.googleapis.com/drive/v3/files/{self.file_id}?fields=parents,name&supportsAllDrives=true", headers=headers)
                    
                    if res_get.status_code == 200:
                        file_info = res_get.json()
                        parents = file_info.get("parents", [])
                        old_name = file_info.get("name", "")
                        
                        # 2. 폴더에서 제거하고 [취소됨] 꼬리표 붙이기 (휴지통 권한이 없으므로 폴더에서 숨김 처리)
                        params = {"supportsAllDrives": "true"}
                        if parents:
                            params["removeParents"] = ",".join(parents)
                            
                        payload = {"name": f"[결재취소] {old_name}"}
                        res_patch = requests.patch(f"https://www.googleapis.com/drive/v3/files/{self.file_id}", params=params, json=payload, headers=headers)
                        if res_patch.status_code not in [200, 204]:
                            raise Exception(f"File Modify Error: {res_patch.text}")
                    elif res_get.status_code != 404:
                        raise Exception(f"File Fetch Error: {res_get.text}")
                        
                manager.execute_with_retry(_remove_file)
                
            # 시트 행 삭제
            ws_raw = manager.get_worksheet(APPROVAL_SPREADSHEET_ID, "전자결재 RAW DATA")
            ws_raw.delete_rows(self.row_idx)
            self.finished.emit(True, "결재 요청 및 관련 서류 파일이 성공적으로 취소되었습니다.")
        except Exception as e:
            self.finished.emit(False, str(e))

class ApprovalCheckInterface(ScrollArea):
    def __init__(self, main_window, parent=None):
        super().__init__(parent=parent)
        self.main_window = main_window
        self.setObjectName("ApprovalCheckInterface")
        
        self.view = QWidget(self)
        self.view.setObjectName('ApprovalCheckView')
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.view.setStyleSheet("QWidget#ApprovalCheckView { background-color: transparent; }")
        
        self.vbox = QVBoxLayout(self.view)
        self.vbox.setContentsMargins(40, 40, 40, 40)
        self.vbox.setSpacing(20)
        
        # 헤더 영역
        header_layout = QHBoxLayout()
        title_vbox = QVBoxLayout()
        
        title = TitleLabel("내 결재 확인")
        title.setFont(QFont("SUIT", 24, QFont.Bold))
        title_vbox.addWidget(title)
        
        subtitle = SubtitleLabel("내가 기안한 결재의 진행 상황을 확인합니다.")
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        title_vbox.addWidget(subtitle)
        
        header_layout.addLayout(title_vbox)
        header_layout.addStretch(1)
        
        self.refresh_btn = PrimaryPushButton("새로고침")
        self.refresh_btn.clicked.connect(self.load_data)
        header_layout.addWidget(self.refresh_btn, alignment=Qt.AlignBottom)
        
        self.vbox.addLayout(header_layout)
        
        # 테이블
        self.card = CardWidget(self)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(20, 20, 20, 20)
        
        self.table = TableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["결재종류", "요청일자", "사유", "기간 날짜", "기간", "진행상태", "승인일자"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 200)
        
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        self.card_layout.addWidget(self.table)
        self.vbox.addWidget(self.card)
        
        self.vbox.addStretch(1)
        
        self.worker = None
        self.is_silent = False
        
        # 10초 자동 새로고침 타이머 설정
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.auto_load_data)
        self.refresh_timer.start(10000) # 10초 (10000ms)
        
    def auto_load_data(self):
        self.load_data(silent=True)
        
    def load_data(self, silent=False):
        self.is_silent = silent
        if not self.is_silent:
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("로딩 중...")
            self.table.setRowCount(0)
        
        self.worker = ApprovalCheckWorker()
        self.worker.finished.connect(self.on_data_loaded)
        self.worker.start()
        
    def on_data_loaded(self, success, records, error_msg):
        if not self.is_silent:
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("새로고침")
        
        if not success:
            if not self.is_silent:
                InfoBar.error("불러오기 실패", error_msg, duration=5000, parent=self)
            return
            
        self.table.setRowCount(len(records))
        for i, record in enumerate(records):
            row_idx = record["row_idx"]
            file_id = record["file_id"]
            row = record["data"]
            
            doc_type = row[1]
            reason = row[3]
            period = row[4]
            period_date = row[5] # 기간 날짜
            req_date = row[6]
            status_val = row[8].strip().upper()
            app_date = row[9]
            
            status_text = "대기중"
            status_color = QColor(200, 200, 200) # Gray
            if status_val == "Y":
                status_text = "승인"
                status_color = QColor(100, 200, 100) # Green
            elif status_val == "N":
                status_text = "반려"
                status_color = QColor(255, 100, 100) # Red
                
            items = [
                QTableWidgetItem(doc_type),
                QTableWidgetItem(req_date),
                QTableWidgetItem(reason),
                QTableWidgetItem(period_date),
                QTableWidgetItem(period),
                QTableWidgetItem(status_text),
                QTableWidgetItem(app_date)
            ]
            
            # 0번째 item에 실제 시트 행 번호를 몰래 숨겨둡니다.
            items[0].setData(Qt.UserRole, row_idx)
            # 1번째 item에 파일 ID를 숨겨둡니다.
            items[1].setData(Qt.UserRole, file_id)
            
            items[5].setForeground(status_color)
            
            for j, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemIsEditable) # Read-only
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, j, item)
                
    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if item is None:
            return
            
        row = item.row()
        status_item = self.table.item(row, 5)
        if status_item.text() != "대기중":
            return
            
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #2b2b2b; color: white; border: 1px solid #3f3f3f; }
            QMenu::item:selected { background-color: #3f3f3f; }
        """)
        cancel_action = QAction("결재 취소", self)
        cancel_action.triggered.connect(lambda: self.cancel_approval(row))
        menu.addAction(cancel_action)
        menu.exec_(self.table.viewport().mapToGlobal(pos))
        
    def cancel_approval(self, row):
        row_idx = self.table.item(row, 0).data(Qt.UserRole)
        file_id = self.table.item(row, 1).data(Qt.UserRole)
        
        reply = QMessageBox.question(self, "결재 취소", "선택한 결재를 취소하시겠습니까?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("취소 중...")
            self.cancel_worker = ApprovalCancelWorker(row_idx, file_id)
            self.cancel_worker.finished.connect(self.on_cancel_finished)
            self.cancel_worker.start()
            
    def on_cancel_finished(self, success, message):
        if success:
            InfoBar.success("성공", message, duration=3000, parent=self)
            self.load_data()
        else:
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("새로고침")
            InfoBar.error("실패", f"취소 실패: {message}", duration=5000, parent=self)
