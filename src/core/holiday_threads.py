import os
import sys
import time
import difflib
from PyQt5.QtCore import QThread, pyqtSignal
from src.config import CREDENTIALS_PATH, SESSION
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = "1giC0dVHS3UYPfKJyfrab9RkinePMYZC3ZWRHQGKrYyw"

def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    return gspread.authorize(creds)

def find_worksheet_by_date(client, date_str):
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    try:
        ws = spreadsheet.worksheet("Raw Checking")
        ws.update_acell('B1', date_str)
        return ws
    except Exception:
        pass
        
    for ws in reversed(spreadsheet.worksheets()):
        try:
            val = ws.cell(1, 2).value
            if val and val.strip() == date_str:
                return ws
        except Exception:
            continue
    return None

class HolidayFetchThread(QThread):
    result_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, date_str):
        super().__init__()
        self.date_str = date_str

    def run(self):
        try:
            client = get_gspread_client()
            sheet = find_worksheet_by_date(client, self.date_str)
            
            if not sheet:
                self.error.emit(f"해당 날짜({self.date_str})가 B1 셀에 지정된 시트를 찾을 수 없습니다.")
                return
                
            records = sheet.get_all_values()
            
            # Parse user columns
            # Row 2 (index 1) has user names
            user_cols = {}
            if len(records) > 1:
                row_users = records[1]
                for col_idx, user_name in enumerate(row_users):
                    if user_name.strip():
                        user_cols[user_name.strip()] = col_idx # 0-indexed column
                        
            data = {}
            # Row 4 (index 3) starts data. Each company takes 3 rows (header, checks, comments).
            # Wait, index 2 is row 3 which is the first company header!
            for i in range(2, len(records), 3):
                if i + 2 < len(records):
                    row_header = records[i]
                    row_checks = records[i+1]
                    row_comments = records[i+2]
                    
                    company_name = ""
                    if len(row_header) > 1:
                        company_name = row_header[1].strip()
                        
                    if not company_name:
                        continue
                        
                    company_data = {"users": {}}
                    for user_name, col_idx in user_cols.items():
                        popup_check = row_checks[col_idx] if col_idx < len(row_checks) else ""
                        place_check = row_checks[col_idx+1] if col_idx+1 < len(row_checks) else ""
                        popup_comment = row_comments[col_idx] if col_idx < len(row_comments) else ""
                        place_comment = row_comments[col_idx+1] if col_idx+1 < len(row_comments) else ""
                        
                        company_data["users"][user_name] = {
                            "popup_check": popup_check.strip(),
                            "place_check": place_check.strip(),
                            "popup_comment": popup_comment.strip(),
                            "place_comment": place_comment.strip()
                        }
                    data[company_name] = company_data
            
            self.result_ready.emit(data)
            
        except Exception as e:
            self.error.emit(str(e))

class HolidayUpdateThread(QThread):
    update_success = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, date_str, local_company_name, popup_check, place_check, popup_comment, place_comment):
        super().__init__()
        self.date_str = date_str
        self.local_company_name = local_company_name
        self.popup_check = popup_check
        self.place_check = place_check
        self.popup_comment = popup_comment
        self.place_comment = place_comment

    def run(self):
        try:
            client = get_gspread_client()
            sheet = find_worksheet_by_date(client, self.date_str)
            
            if not sheet:
                self.error.emit(f"해당 날짜({self.date_str})가 B1 셀에 지정된 시트를 찾을 수 없습니다.")
                return
                
            records = sheet.get_all_values()
            
            current_user = SESSION.get("name", "").strip()
            if not current_user:
                self.error.emit("로그인 정보(이름)를 확인할 수 없습니다.")
                return
                
            user_col_idx = -1
            if len(records) > 1:
                for idx, name in enumerate(records[1]):
                    if name.strip() == current_user:
                        user_col_idx = idx
                        break
                        
            if user_col_idx == -1:
                self.error.emit(f"시트에서 '{current_user}' 작업자의 열을 찾을 수 없습니다.")
                return
                
            # Find the company row using fuzzy matching
            sheet_companies = []
            # Each company is 3 rows, starting at index 2
            for i in range(2, len(records), 3):
                if i < len(records) and len(records[i]) > 1 and records[i][1].strip():
                    sheet_companies.append((records[i][1].strip(), i))
                    
            if not sheet_companies:
                self.error.emit("시트에 등록된 업체가 없습니다.")
                return
                
            company_names = [c[0] for c in sheet_companies]
            
            # Improved matching: exact -> substring -> difflib
            matched_name = ""
            local_clean = self.local_company_name.replace(" ", "")
            
            # 1. Exact match
            if self.local_company_name in company_names:
                matched_name = self.local_company_name
            
            # 2. Substring match
            if not matched_name:
                for cand in company_names:
                    cand_clean = cand.replace(" ", "")
                    if local_clean in cand_clean or cand_clean in local_clean:
                        matched_name = cand
                        break
                        
            # 3. difflib fuzzy match
            if not matched_name:
                matches = difflib.get_close_matches(self.local_company_name, company_names, n=1, cutoff=0.3)
                if matches:
                    matched_name = matches[0]
            
            target_row_idx = -1
            if matched_name:
                for name, idx in sheet_companies:
                    if name == matched_name:
                        target_row_idx = idx
                        break
            else:
                self.error.emit(f"시트에서 '{self.local_company_name}'와 유사한 업체를 찾을 수 없습니다.")
                return
                
            # Update cells
            # target_row_idx is 0-indexed index of the header row (e.g. 2 for Row 3).
            # The checks row is target_row_idx + 1 (e.g. 3 for Row 4).
            # The comments row is target_row_idx + 2 (e.g. 4 for Row 5).
            # In gspread, row indices are 1-indexed.
            checks_row_gspread = target_row_idx + 2    # target_row_idx (2) + 2 = 4
            comments_row_gspread = target_row_idx + 3  # target_row_idx (2) + 3 = 5
            
            popup_col_gspread = user_col_idx + 1
            place_col_gspread = user_col_idx + 2
            
            cells_to_update = [
                gspread.Cell(checks_row_gspread, popup_col_gspread, self.popup_check),
                gspread.Cell(checks_row_gspread, place_col_gspread, self.place_check),
                gspread.Cell(comments_row_gspread, popup_col_gspread, self.popup_comment),
                gspread.Cell(comments_row_gspread, place_col_gspread, self.place_comment)
            ]
            
            sheet.update_cells(cells_to_update)
            self.update_success.emit()
            
        except Exception as e:
            self.error.emit(f"업데이트 중 오류 발생: {str(e)}")

class HolidayBatchUpdateThread(QThread):
    update_success = pyqtSignal(int)
    error = pyqtSignal(str)
    
    def __init__(self, date_str, update_data_dict):
        super().__init__()
        self.date_str = date_str
        self.update_data = update_data_dict
        
    def run(self):
        try:
            client = get_gspread_client()
            sheet = find_worksheet_by_date(client, self.date_str)
            if not sheet:
                self.error.emit(f"해당 날짜({self.date_str})가 B1 셀에 지정된 시트를 찾을 수 없습니다.")
                return
                
            records = sheet.get_all_values()
            current_user = SESSION.get("name", "").strip()
            if not current_user:
                self.error.emit("로그인 정보(이름)를 확인할 수 없습니다.")
                return
                
            user_col_idx = -1
            if len(records) > 1:
                for idx, name in enumerate(records[1]):
                    if name.strip() == current_user:
                        user_col_idx = idx
                        break
                        
            if user_col_idx == -1:
                self.error.emit(f"시트에서 '{current_user}' 작업자의 열을 찾을 수 없습니다.")
                return
                
            sheet_companies = []
            for i in range(2, len(records), 3):
                if i < len(records) and len(records[i]) > 1 and records[i][1].strip():
                    sheet_companies.append((records[i][1].strip(), i))
                    
            if not sheet_companies:
                self.error.emit("시트에 등록된 업체가 없습니다.")
                return
                
            company_names = [c[0] for c in sheet_companies]
            
            data_updates = []
            updated_count = 0
            
            for local_name, data in self.update_data.items():
                matched_name = ""
                local_clean = local_name.replace(" ", "")
                
                if local_name in company_names:
                    matched_name = local_name
                
                if not matched_name:
                    for cand in company_names:
                        cand_clean = cand.replace(" ", "")
                        if local_clean in cand_clean or cand_clean in local_clean:
                            matched_name = cand
                            break
                            
                if not matched_name:
                    matches = difflib.get_close_matches(local_name, company_names, n=1, cutoff=0.3)
                    if matches:
                        matched_name = matches[0]
                
                target_row_idx = -1
                if matched_name:
                    for name, idx in sheet_companies:
                        if name == matched_name:
                            target_row_idx = idx
                            break
                            
                if target_row_idx != -1:
                    checks_row = target_row_idx + 2
                    comments_row = target_row_idx + 3
                    popup_col = user_col_idx + 1
                    place_col = user_col_idx + 2
                    
                    popup_check_a1 = gspread.utils.rowcol_to_a1(checks_row, popup_col)
                    place_check_a1 = gspread.utils.rowcol_to_a1(checks_row, place_col)
                    popup_comment_a1 = gspread.utils.rowcol_to_a1(comments_row, popup_col)
                    place_comment_a1 = gspread.utils.rowcol_to_a1(comments_row, place_col)
                    
                    data_updates.append({'range': popup_check_a1, 'values': [[data.get('popup_val', '')]]})
                    data_updates.append({'range': place_check_a1, 'values': [[data.get('place_val', '')]]})
                    data_updates.append({'range': popup_comment_a1, 'values': [[data.get('popup_comment', '')]]})
                    data_updates.append({'range': place_comment_a1, 'values': [[data.get('place_comment', '')]]})
                    
                    updated_count += 1
                    
            if data_updates:
                sheet.batch_update(data_updates, value_input_option='USER_ENTERED')
                self.update_success.emit(updated_count)
            else:
                self.error.emit("업데이트할 데이터가 없거나 매칭된 업체가 없습니다.")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(f"업데이트 중 오류 발생: {str(e)}")
