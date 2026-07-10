import os
import sys
import json
import time
import datetime
import urllib.parse
import re
import random
import hashlib
import tempfile
import threading
import requests
from bs4 import BeautifulSoup
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, SETTINGS_PATH, CREDENTIALS_PATH, SPREADSHEET_ID
from src.core.google_sheets_manager import GoogleSheetsManager

import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import gspread


class ScheduleFetchThread(QThread):
    data_fetched = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, sheet_name="schedule"):
        super().__init__()
        self.sheet_name = sheet_name
        
    def run(self):

        try:
            manager = GoogleSheetsManager()
            
            def _fetch():
                client = manager.get_client()
                import urllib.parse
                sort_range = urllib.parse.quote('정렬기준!A:A')
                url = f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?includeGridData=true&ranges={self.sheet_name}!A:C&ranges=holidays!A:B&ranges={sort_range}'
                return client.http_client.request('get', url)
            
            res = manager.execute_with_retry(_fetch)
            
            if res.status_code != 200:
                self.error_occurred.emit("데이터를 가져오는데 실패했습니다.")
                return

            sheets = res.json().get('sheets', [])
            
            schedule_grid = []
            holidays_grid = []
            sort_grid = []
            
            for sheet in sheets:
                title = sheet.get('properties', {}).get('title', '')
                grid_data = sheet.get('data', [{}])[0].get('rowData', [])
                if title == self.sheet_name:
                    schedule_grid = grid_data
                elif title == 'holidays':
                    holidays_grid = grid_data
                elif title == '정렬기준':
                    sort_grid = grid_data
                    

            parsed_data = []
            for row in schedule_grid:
                if 'values' in row and len(row['values']) >= 2:
                    date_val = row['values'][0].get('formattedValue', '')
                    text_val = row['values'][1].get('formattedValue', '')
                    
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
                    
                    creator_id = ''
                    if len(row['values']) >= 3:
                        creator_id = row['values'][2].get('formattedValue', '')
                    parsed_data.append([date_val, text_val, color_hex, creator_id])
            
            parsed_holidays = {}
            parsed_holidays = {}
            import re
            for row in holidays_grid:
                if 'values' in row and len(row['values']) >= 2:
                    date_val = row['values'][0].get('formattedValue', '')
                    text_val = row['values'][1].get('formattedValue', '')
                    if date_val and text_val:
                        match = re.search(r'(\d{4}-\d{2}-\d{2})', date_val)
                        if match:
                            parsed_holidays[match.group(1)] = text_val
                            
            sort_order = ['김현우', '공훈식', '김태훈', '장여진', '김정원', '김가현', '김태형', '이승희', '홍지민']
            if sort_grid:
                fetched_order = []
                for row in sort_grid:
                    if 'values' in row and len(row['values']) > 0:
                        val = row['values'][0].get('formattedValue', '')
                        if val:
                            val = val.strip()
                            if val and val != '이름':
                                fetched_order.append(val)
                if fetched_order:
                    sort_order = fetched_order

            def get_rank(item):
                text_val = item[1]
                for idx, name in enumerate(sort_order):
                    if name in text_val:
                        return idx
                return 999
            
            parsed_data.sort(key=get_rank)
            
            self.data_fetched.emit({'schedules': parsed_data, 'holidays': parsed_holidays})
        except Exception as e:
            self.error_occurred.emit(str(e))


class ScheduleAddThread(QThread):
    error_occurred = pyqtSignal(str)
    
    def __init__(self, start_date, end_date, text, creator_id, sheet_name="schedule"):
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date
        self.text = text
        self.creator_id = creator_id
        self.sheet_name = sheet_name
        
    def run(self):

        try:
            manager = GoogleSheetsManager()
            sheet = manager.get_worksheet(SPREADSHEET_ID, self.sheet_name)
            
            from datetime import datetime, timedelta
            start = datetime.strptime(self.start_date, "%Y-%m-%d")
            end = datetime.strptime(self.end_date, "%Y-%m-%d")
            
            rows_to_add = []
            current = start
            while current <= end:
                rows_to_add.append([current.strftime("%Y-%m-%d"), self.text, self.creator_id])
                current += timedelta(days=1)
                
            if len(rows_to_add) > 1:
                sheet.append_rows(rows_to_add)
            elif len(rows_to_add) == 1:
                sheet.append_row(rows_to_add[0])
                
        except Exception as e:
            self.error_occurred.emit(str(e))


class ScheduleDeleteThread(QThread):
    error_occurred = pyqtSignal(str)
    success = pyqtSignal()
    
    def __init__(self, date_str, text, creator_id, sheet_name="schedule"):
        super().__init__()
        self.date_str = date_str
        self.text = text
        self.creator_id = creator_id
        self.sheet_name = sheet_name
        
    def run(self):

        try:
            manager = GoogleSheetsManager()
            sheet = manager.get_worksheet(SPREADSHEET_ID, self.sheet_name)
            
            records = sheet.get_all_values()
            found_index = -1
            for i, row in enumerate(records):
                if len(row) >= 3 and row[0] == self.date_str and row[1] == self.text and row[2] == self.creator_id:
                    found_index = i + 1  # 1-indexed for gspread
                    break
                    
            if found_index != -1:
                sheet.delete_rows(found_index)
                self.success.emit()
            else:
                self.error_occurred.emit("삭제할 일정을 구글 시트에서 찾을 수 없습니다.")
                
        except Exception as e:
            self.error_occurred.emit(str(e))

