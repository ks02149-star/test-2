import os
import json
import datetime
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QUrl, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QSplitter
from PyQt5.QtGui import QFont, QDesktopServices
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineScript, QWebEngineProfile, QWebEnginePage
from qfluentwidgets import (TitleLabel, SubtitleLabel, PushButton, PrimaryPushButton, 
                            CalendarPicker, ScrollArea, LineEdit, InfoBar, InfoBarPosition, qconfig)
from src.utils.helpers import load_companies
from src.ui.components.cards import CrossCheckListCard
from src.core.holiday_threads import HolidayFetchThread, HolidayUpdateThread, HolidayBatchUpdateThread
from src.config import SESSION

class HolidayCheckInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("HolidayCheckInterface")
        self.companies = []
        self.cross_check_data = {}
        self.selected_company = None
        self.current_date_str = datetime.date.today().strftime("%Y-%m-%d")
        self.setup_ui()
        self.load_local_companies()
        
        # Initial fetch
        QTimer.singleShot(500, self.fetch_data)
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # Splitter for Left (List) and Right (Web Views)
        self.splitter = QSplitter(Qt.Horizontal, self)
        main_layout.addWidget(self.splitter, 1)
        
        # --- Left Panel ---
        left_panel = QFrame(self)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title and Sheet Shortcut
        title_layout = QHBoxLayout()
        self.title_label = TitleLabel("업체별 휴진 체크", self)
        title_layout.addWidget(self.title_label)
        
        title_layout.addStretch(1)
        
        self.sheet_shortcut_btn = PushButton("시트 바로가기", self)
        self.sheet_shortcut_btn.clicked.connect(self.open_google_sheet)
        title_layout.addWidget(self.sheet_shortcut_btn)
        
        left_layout.addLayout(title_layout)
        
        left_layout.addSpacing(25)
        
        # Fixed Date Label (looks like CalendarPicker but unclickable)
        self.date_picker = CalendarPicker(self)
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.date_picker.setFocusPolicy(Qt.NoFocus)
        left_layout.addWidget(self.date_picker)
        
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 10, 0)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.addStretch(1)
        self.scroll_area.setWidget(self.scroll_content)
        left_layout.addWidget(self.scroll_area)
        
        # --- Right Panel ---
        right_panel = QFrame(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)
        
        # Web Views Splitter (Horizontal for side-by-side)
        self.web_splitter = QSplitter(Qt.Horizontal, self)
        
        self.popup_view = QWebEngineView(self)
        self.place_view = QWebEngineView(self)
        
        # Use Mobile UA for popup_view to show mobile sites, and Desktop UA for place_view to avoid bot detection
        mobile_ua = "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
        desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # popup_view needs a separate profile so its UA doesn't override the global default profile used by place_view
        mobile_profile = QWebEngineProfile("MobileProfile", self)
        mobile_profile.setHttpUserAgent(mobile_ua)
        mobile_page = QWebEnginePage(mobile_profile, self.popup_view)
        self.popup_view.setPage(mobile_page)
        
        self.place_view.page().profile().setHttpUserAgent(desktop_ua)
        
        empty_html = "<body style='background-color: #1e1e1e; color: #a0a0a0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; font-family: sans-serif;'><h2 style='font-size: 14px;'>등록된 URL이 없습니다.</h2></body>"
        self.popup_view.setHtml(empty_html)
        self.place_view.setHtml(empty_html)
        
        self.web_splitter.addWidget(self.popup_view)
        self.web_splitter.addWidget(self.place_view)
        
        right_layout.addWidget(self.web_splitter, 1)
        
        # Bottom Control Bar
        self.control_bar = QFrame(self)
        self.control_bar.setStyleSheet("QFrame { background-color: #2c2c2c; border-radius: 8px; padding: 5px; border: 1px solid #3c3c3c; }")
        control_layout = QHBoxLayout(self.control_bar)
        
        control_layout.addSpacing(30)
        
        def make_section_label(text):
            lbl = QLabel(text, self)
            lbl.setFixedSize(70, 30)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("background-color: white; color: black; border-radius: 4px; font-weight: bold;")
            return lbl
            
        # Popup controls
        control_layout.addWidget(make_section_label("팝업"))
        self.popup_o_btn = PushButton("O", self)
        self.popup_o_btn.setFixedSize(40, 40)
        self.popup_x_btn = PushButton("X", self)
        self.popup_x_btn.setFixedSize(40, 40)
        self.popup_na_btn = PushButton("■", self)
        self.popup_na_btn.setFixedSize(40, 40)
        
        btn_font = QFont("SUIT", 13, QFont.Bold)
        o_style = "QPushButton { background-color: #3c3c3c; border-radius: 4px; color: white; } QPushButton:checked { background-color: #2e7d32; border: 2px solid #4caf50; }"
        x_style = "QPushButton { background-color: #3c3c3c; border-radius: 4px; color: white; } QPushButton:checked { background-color: #c62828; border: 2px solid #ef5350; }"
        na_style = "QPushButton { background-color: #3c3c3c; border-radius: 4px; color: white; } QPushButton:checked { background-color: #555555; border: 2px solid #888888; }"
        
        self.popup_o_btn.setStyleSheet(o_style)
        self.popup_x_btn.setStyleSheet(x_style)
        self.popup_na_btn.setStyleSheet(na_style)
        
        for btn in [self.popup_o_btn, self.popup_x_btn, self.popup_na_btn]:
            btn.setCheckable(True)
            btn.setFont(btn_font)
            btn.clicked.connect(self.on_popup_btn_clicked)
            control_layout.addWidget(btn)
            
        self.popup_reason_input = LineEdit(self)
        self.popup_reason_input.setPlaceholderText("수정사항")
        control_layout.addWidget(self.popup_reason_input)
        
        control_layout.addSpacing(30)
        
        v_sep = QFrame(self)
        v_sep.setFrameShape(QFrame.VLine)
        v_sep.setFrameShadow(QFrame.Plain)
        v_sep.setStyleSheet("color: rgba(255, 255, 255, 0.15);")
        control_layout.addWidget(v_sep)
        
        control_layout.addSpacing(30)
        
        # Place controls
        control_layout.addWidget(make_section_label("플레이스"))
        self.place_o_btn = PushButton("O", self)
        self.place_o_btn.setFixedSize(40, 40)
        self.place_x_btn = PushButton("X", self)
        self.place_x_btn.setFixedSize(40, 40)
        
        self.place_o_btn.setStyleSheet(o_style)
        self.place_x_btn.setStyleSheet(x_style)
        
        for btn in [self.place_o_btn, self.place_x_btn]:
            btn.setCheckable(True)
            btn.setFont(btn_font)
            btn.clicked.connect(self.on_place_btn_clicked)
            control_layout.addWidget(btn)
            
        self.place_reason_input = LineEdit(self)
        self.place_reason_input.setPlaceholderText("수정사항")
        control_layout.addWidget(self.place_reason_input)
        
        control_layout.addStretch(1)
        
        self.save_btn = PushButton("단일 저장", self)
        self.save_btn.setFont(QFont("SUIT", 11, QFont.Bold))
        self.save_btn.clicked.connect(self.save_data)
        control_layout.addWidget(self.save_btn)
        
        self.next_btn = PrimaryPushButton("다음 업체 ->", self)
        self.next_btn.setFont(QFont("SUIT", 11, QFont.Bold))
        self.next_btn.clicked.connect(self.select_next_company)
        control_layout.addWidget(self.next_btn)
        
        right_layout.addWidget(self.control_bar)
        
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([300, 700])
        
    def open_google_sheet(self):
        from src.core.holiday_threads import SPREADSHEET_ID
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
        QDesktopServices.openUrl(QUrl(url))
        
    def save_current_to_memory(self):
        if not self.selected_company: return
        comp_name = self.selected_company.get('name')
        
        popup_val = ""
        if self.popup_o_btn.isChecked(): popup_val = "O"
        elif self.popup_x_btn.isChecked(): popup_val = "X"
        elif self.popup_na_btn.isChecked(): popup_val = "■"
            
        place_val = ""
        if self.place_o_btn.isChecked(): place_val = "O"
        elif self.place_x_btn.isChecked(): place_val = "X"
            
        # Update user's data locally
        my_name = SESSION.get('name', '')
        if my_name:
            if comp_name not in self.cross_check_data:
                self.cross_check_data[comp_name] = {'users': {}}
            if 'users' not in self.cross_check_data[comp_name]:
                self.cross_check_data[comp_name]['users'] = {}
                
            self.cross_check_data[comp_name]['users'][my_name] = {
                'popup_check': popup_val,
                'popup_comment': self.popup_reason_input.text().strip(),
                'place_check': place_val,
                'place_comment': self.place_reason_input.text().strip()
            }
            
            for card in getattr(self, 'card_widgets', []):
                if card.company_data.get('name') == comp_name:
                    card.update_summary(self.cross_check_data[comp_name])
                    break

    def select_next_company(self):
        if not self.companies or not self.selected_company:
            return
            
        if self.next_btn.text() == "일괄 저장":
            self.save_current_to_memory()
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(self, '일괄 저장', '리스트의 모든 업체 체크가 완료되었습니다. 일괄 저장하시겠습니까?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.batch_save_data()
            return
            
        # Save current state to memory before advancing
        self.save_current_to_memory()
            
        current_name = self.selected_company.get('name')
        current_idx = -1
        for i, comp in enumerate(self.companies):
            if comp.get('name') == current_name:
                current_idx = i
                break
                
        if current_idx != -1 and current_idx + 1 < len(self.companies):
            next_company = self.companies[current_idx + 1]
            self.on_company_selected(next_company)
            
            # Scroll to the selected card
            for card in getattr(self, 'card_widgets', []):
                if card.company_data.get('name') == next_company.get('name'):
                    self.scroll_area.ensureWidgetVisible(card)
                    break

    def load_local_companies(self):
        self.companies = load_companies()
        self.render_list()
        
    def get_matched_company_name(self, local_name):
        import difflib
        sheet_names = list(self.cross_check_data.keys())
        
        matched_name = ""
        local_clean = local_name.replace(" ", "")
        
        if local_name in sheet_names:
            matched_name = local_name
        
        if not matched_name:
            for cand in sheet_names:
                cand_clean = cand.replace(" ", "")
                if local_clean in cand_clean or cand_clean in local_clean:
                    matched_name = cand
                    break
                    
        if not matched_name:
            matches = difflib.get_close_matches(local_name, sheet_names, n=1, cutoff=0.3)
            if matches:
                matched_name = matches[0]
                
        return matched_name
        
    def render_list(self):
        # Always reload companies so external edits are reflected immediately
        self.companies = load_companies()
        
        # Clear layout
        while self.scroll_layout.count() > 1:
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self.card_widgets = []
        for comp in self.companies:
            comp_name = comp.get('name', '')
            matched_name = self.get_matched_company_name(comp_name)
            check_data = self.cross_check_data.get(matched_name, {}) if matched_name else {}
            card = CrossCheckListCard(comp, check_data, self)
            card.clicked.connect(self.on_company_selected)
            
            # Re-select if this is the currently selected company
            if self.selected_company and self.selected_company.get('name') == comp_name:
                card.set_selected(True)
                
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, card)
            self.card_widgets.append(card)
            

    def fetch_data(self):
        if not hasattr(self, 'running_threads'):
            self.running_threads = []
            
        thread = HolidayFetchThread(self.current_date_str)
        
        def cleanup(t=thread):
            if t in getattr(self, 'running_threads', []):
                self.running_threads.remove(t)
                
        thread.result_ready.connect(self.on_data_fetched)
        thread.error.connect(self.on_fetch_error)
        thread.finished.connect(cleanup)
        
        self.running_threads.append(thread)
        thread.start()
        
    def on_data_fetched(self, data):
        self.cross_check_data = data
        self.render_list()
        
    def on_fetch_error(self, err_msg):
        # Only show if not just a background refresh error
        pass
        
    def on_company_selected(self, company_data):
        if getattr(self, 'selected_company', None) and self.selected_company.get('name') != company_data.get('name'):
            self.save_current_to_memory()
            
        self.selected_company = company_data
        
        for card in getattr(self, 'card_widgets', []):
            card.set_selected(card.company_data.get('name') == company_data.get('name'))
            
        current_idx = -1
        for i, comp in enumerate(self.companies):
            if comp.get('name') == company_data.get('name'):
                current_idx = i
                break
                
        if current_idx != -1 and current_idx == len(self.companies) - 1:
            self.next_btn.setText("일괄 저장")
        else:
            self.next_btn.setText("다음 업체 ->")
            
        popup_url = company_data.get('homepage', '')
        place_url = company_data.get('place', '')
        
        if popup_url:
            if not popup_url.startswith("http"): popup_url = "https://" + popup_url
            self.popup_view.setUrl(QUrl(popup_url))
        else:
            empty_html = "<body style='background-color: #1e1e1e; color: #a0a0a0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; font-family: sans-serif;'><h2 style='font-size: 14px;'>등록된 팝업(홈페이지) URL이 없습니다.</h2></body>"
            self.popup_view.setHtml(empty_html)
            
        if place_url:
            if not place_url.startswith("http"): place_url = "https://" + place_url
            
            # Extract ID and category to use pcmap iframe URL directly!
            # This perfectly isolates the info panel without loading the map at all.
            import re
            match = re.search(r'(place|hospital|restaurant)/(\d+)', place_url)
            if match:
                category = match.group(1)
                place_id = match.group(2)
                place_url = f"https://pcmap.place.naver.com/{category}/{place_id}/home"
                
            self.place_view.setUrl(QUrl(place_url))
        else:
            empty_html = "<body style='background-color: #1e1e1e; color: #a0a0a0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; font-family: sans-serif;'><h2 style='font-size: 14px;'>등록된 플레이스 URL이 없습니다.</h2></body>"
            self.place_view.setHtml(empty_html)
            
        # Reset buttons and text
        for btn in [self.popup_o_btn, self.popup_x_btn, self.popup_na_btn, self.place_o_btn, self.place_x_btn]:
            btn.setChecked(False)
        self.popup_reason_input.clear()
        self.place_reason_input.clear()
        
        # Try to load my own previous check if it exists in cross_check_data
        my_name = SESSION.get('name', '')
        if my_name and self.cross_check_data:
            local_name = company_data.get('name', '')
            matched_name = self.get_matched_company_name(local_name)
                    
            if matched_name:
                comp_data = self.cross_check_data.get(matched_name, {}).get('users', {}).get(my_name, {})
                if comp_data:
                    p_chk = comp_data.get('popup_check', '')
                    if p_chk == 'O': self.popup_o_btn.setChecked(True)
                    elif p_chk == 'X': self.popup_x_btn.setChecked(True)
                    elif p_chk == '■': self.popup_na_btn.setChecked(True)
                    
                    pl_chk = comp_data.get('place_check', '')
                    if pl_chk == 'O': self.place_o_btn.setChecked(True)
                    elif pl_chk == 'X': self.place_x_btn.setChecked(True)
                    
                    self.popup_reason_input.setText(comp_data.get('popup_comment', ''))
                    self.place_reason_input.setText(comp_data.get('place_comment', ''))
                
    def on_popup_btn_clicked(self):
        sender = self.sender()
        for btn in [self.popup_o_btn, self.popup_x_btn, self.popup_na_btn]:
            if btn != sender:
                btn.setChecked(False)
                
    def on_place_btn_clicked(self):
        sender = self.sender()
        for btn in [self.place_o_btn, self.place_x_btn]:
            if btn != sender:
                btn.setChecked(False)
                
    def save_data(self):
        if not self.selected_company:
            InfoBar.warning("선택된 업체 없음", "먼저 업체를 선택해주세요.", parent=self, position=InfoBarPosition.TOP)
            return
            
        popup_check = ""
        if self.popup_o_btn.isChecked(): popup_check = "O"
        elif self.popup_x_btn.isChecked(): popup_check = "X"
        elif self.popup_na_btn.isChecked(): popup_check = "■"
        
        place_check = ""
        if self.place_o_btn.isChecked(): place_check = "O"
        elif self.place_x_btn.isChecked(): place_check = "X"
        
        popup_comment = self.popup_reason_input.text().strip()
        place_comment = self.place_reason_input.text().strip()
        
        self.save_btn.setEnabled(False)
        self.save_btn.setText("저장 중...")
        
        if not hasattr(self, 'running_threads'):
            self.running_threads = []
            
        thread = HolidayUpdateThread(
            self.current_date_str,
            self.selected_company.get('name', ''),
            popup_check,
            place_check,
            popup_comment,
            place_comment
        )
        
        def cleanup(t=thread):
            if t in getattr(self, 'running_threads', []):
                self.running_threads.remove(t)
                
        thread.update_success.connect(self.on_update_success)
        thread.error.connect(self.on_update_error)
        thread.finished.connect(cleanup)
        
        self.running_threads.append(thread)
        thread.start()
        
    def on_update_success(self):
        self.save_btn.setEnabled(True)
        self.save_btn.setText("단일 저장")
        InfoBar.success("저장 완료", "구글 시트에 성공적으로 저장되었습니다.", parent=self, position=InfoBarPosition.TOP)
        self.fetch_data() # refresh
        
    def on_update_error(self, err_msg):
        self.save_btn.setEnabled(True)
        self.save_btn.setText("단일 저장")
        InfoBar.error("저장 실패", err_msg, parent=self, position=InfoBarPosition.TOP)

    def batch_save_data(self):
        my_name = SESSION.get('name', '')
        if not my_name:
            InfoBar.warning("로그인 오류", "로그인 정보를 확인할 수 없습니다.", parent=self, position=InfoBarPosition.TOP)
            return
            
        # Extract my own data from cross_check_data
        update_data = {}
        for comp_name, comp_info in self.cross_check_data.items():
            if 'users' in comp_info and my_name in comp_info['users']:
                user_data = comp_info['users'][my_name]
                if user_data.get('popup_check') or user_data.get('place_check') or user_data.get('popup_comment') or user_data.get('place_comment'):
                    update_data[comp_name] = {
                        'popup_val': user_data.get('popup_check', ''),
                        'popup_comment': user_data.get('popup_comment', ''),
                        'place_val': user_data.get('place_check', ''),
                        'place_comment': user_data.get('place_comment', '')
                    }
                    
        if not update_data:
            InfoBar.warning("저장할 데이터 없음", "일괄 저장할 데이터가 없습니다.", parent=self, position=InfoBarPosition.TOP)
            return
            
        self.next_btn.setEnabled(False)
        self.next_btn.setText("저장 중...")
        
        if not hasattr(self, 'running_threads'):
            self.running_threads = []
            
        thread = HolidayBatchUpdateThread(self.current_date_str, update_data)
        
        def cleanup(t=thread):
            if t in getattr(self, 'running_threads', []):
                self.running_threads.remove(t)
                
        thread.update_success.connect(self.on_batch_success)
        thread.error.connect(self.on_batch_error)
        thread.finished.connect(cleanup)
        
        self.running_threads.append(thread)
        thread.start()
        
    def on_batch_success(self, count):
        self.next_btn.setEnabled(True)
        self.next_btn.setText("일괄 저장")
        InfoBar.success("일괄 저장 완료", f"총 {count}개 업체의 데이터가 구글 시트에 일괄 저장되었습니다.", parent=self, position=InfoBarPosition.TOP)
        self.fetch_data()
        
    def on_batch_error(self, err_msg):
        self.next_btn.setEnabled(True)
        self.next_btn.setText("일괄 저장")
        InfoBar.error("일괄 저장 실패", err_msg, parent=self, position=InfoBarPosition.TOP)
