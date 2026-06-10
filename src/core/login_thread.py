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
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, SETTINGS_PATH, CREDENTIALS_PATH

class LoginThread(QThread):
    success = pyqtSignal(dict)
    error = pyqtSignal(str)
    signup_success = pyqtSignal(str)
    
    def __init__(self, mode, user_id, password, name="", spreadsheet_id="1wWLxMTY3D5urtn0gomepgA1blQnyz05BUi2wepWBTDk"):
        super().__init__()
        self.mode = mode
        self.user_id = user_id
        self.password = password
        self.name = name
        self.spreadsheet_id = spreadsheet_id
        
    def run(self):
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
        from oauth2client.service_account import ServiceAccountCredentials
        try:
            base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            creds_path = CREDENTIALS_PATH
            if not os.path.exists(creds_path):
                self.error.emit("credentials.json 파일을 찾을 수 없습니다.")
                return

            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
            client = gspread.authorize(creds)
            
            try:
                sheet = client.open_by_key(self.spreadsheet_id).worksheet("users")
            except gspread.exceptions.WorksheetNotFound:
                self.error.emit("스프레드시트에 'users' 탭이 없습니다.")
                return
            
            records = sheet.get_all_values()
            
            # Hash password
            hashed_pw = hashlib.sha256(self.password.encode('utf-8')).hexdigest()
            
            if self.mode == "auto_login":
                for row in records[1:]:
                    if len(row) >= 3:
                        r_id, r_pw, r_name = row[0], row[1], row[2]
                        if r_id == self.user_id and r_pw == self.password:
                            self.success.emit({"id": r_id, "name": r_name})
                            return
                self.error.emit("자동 로그인 실패")
                return

            if self.mode == "login":
                for row in records[1:]: # Skip header
                    if len(row) >= 3:
                        r_id, r_pw, r_name = row[0], row[1], row[2]
                        if r_id == self.user_id:
                            if r_pw == hashed_pw:
                                self.success.emit({"id": r_id, "name": r_name})
                                return
                            else:
                                self.error.emit("비밀번호가 일치하지 않습니다.")
                                return
                self.error.emit("존재하지 않는 아이디입니다.")
                
            elif self.mode == "signup":
                for row in records[1:]:
                    if len(row) >= 1 and row[0] == self.user_id:
                        self.error.emit("이미 존재하는 아이디입니다.")
                        return
                
                sheet.append_row([self.user_id, hashed_pw, self.name])
                self.signup_success.emit("회원가입이 완료되었습니다. 로그인해주세요.")
                
        except Exception as e:
            self.error.emit(str(e))

