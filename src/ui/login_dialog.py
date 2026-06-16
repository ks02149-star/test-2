import hashlib
import os
import sys
import json
import time
import datetime
from datetime import date
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QUrl, QDate, QPropertyAnimation, QEasingCurve, QRect, QPoint, QMargins, QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QDialog, QFrame, QLabel, QStackedWidget, QGraphicsDropShadowEffect, QCalendarWidget, QPushButton, QFileDialog, QSizePolicy, QGridLayout, QLineEdit, QCheckBox
from PyQt5.QtGui import QFont, QFontDatabase, QDesktopServices, QTextCharFormat, QColor, QBrush, QPainter, QCursor, QPixmap

from src.core.login_thread import LoginThread
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, FONT_DIR, SETTINGS_PATH, CREDENTIALS_PATH
from src.utils.helpers import safe_json_load, safe_json_save

class PreWarmThread(QThread):
    def run(self):
        try:
            import pandas
            time.sleep(0.1)
            import bs4
            time.sleep(0.1)
            import openpyxl
            time.sleep(0.1)
            import selenium
        except ImportError:
            pass

class LoginDialog(QDialog):
    login_success = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(850, 550)
        
        # Load auto-login settings
        self.base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        self.settings_path = os.path.join(self.base_dir, "Workspace", "settings.json")
        self.auto_login_data = None
        self.load_settings()
        
        self.init_ui()
        
        # Start background pre-warming for heavy packages
        self.prewarm_thread = PreWarmThread()
        self.prewarm_thread.start()
        
        # Check auto-login
        if self.auto_login_data and self.auto_login_data.get("auto_login"):
            self.do_auto_login()

    def load_settings(self):
        self.auto_login_data = safe_json_load(self.settings_path, default=None)

    def save_settings(self, user_id, hashed_pw, auto_login):
        data = safe_json_load(self.settings_path, default={})
        data["auto_login"] = auto_login
        if auto_login:
            data["saved_id"] = user_id
            data["saved_pw"] = hashed_pw
        else:
            data.pop("saved_id", None)
            data.pop("saved_pw", None)
            
        safe_json_save(self.settings_path, data)

    def init_ui(self):
        # Extract the font family set by QApplication
        ff = self.font().family()

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main background container
        self.container = QFrame(self)
        self.container.setStyleSheet("QFrame { background-color: transparent; }")
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(0)
        
        # Add shadow to container
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 0)
        
        # Inner wrapper
        self.wrapper = QFrame(self.container)
        self.wrapper.setGraphicsEffect(shadow)
        self.wrapper.setStyleSheet(f"QFrame#wrapper {{ border-radius: 16px; background-color: white; font-family: '{ff}'; }}")
        self.wrapper.setObjectName("wrapper")
        wrapper_layout = QHBoxLayout(self.wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        
        # --- Left Side (Dark Blue) ---
        self.left_frame = QFrame(self.wrapper)
        self.left_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0a1128, stop:1 #1c2e4a);
                border-top-left-radius: 16px;
                border-bottom-left-radius: 16px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                font-family: "{ff}";
            }}
        """)
        left_layout = QVBoxLayout(self.left_frame)
        left_layout.setContentsMargins(40, 60, 40, 60)
        
        logo_label = QLabel(self.left_frame)
        pixmap = QPixmap(os.path.join(ASSETS_DIR, "images", "logo.png"))
        if not pixmap.isNull():
            logo_label.setPixmap(pixmap.scaledToHeight(40, Qt.SmoothTransformation))
        logo_label.setStyleSheet("background: transparent;")
        
        welcome_title = QLabel("푸름애드\n관리 프로그램", self.left_frame)
        welcome_title.setStyleSheet(f"color: white; font-family: '{ff}'; font-size: 36px; font-weight: bold; background: transparent;")
        
        welcome_sub = QLabel("계속하시려면 로그인이 필요합니다.", self.left_frame)
        welcome_sub.setStyleSheet(f"color: #a0aec0; font-family: '{ff}'; font-size: 14px; background: transparent;")
        
        left_layout.addWidget(logo_label)
        left_layout.addStretch(1)
        left_layout.addWidget(welcome_title)
        left_layout.addSpacing(10)
        left_layout.addWidget(welcome_sub)
        left_layout.addStretch(1)
        
        # --- Right Side (White Card) ---
        self.right_frame = QFrame(self.wrapper)
        self.right_frame.setFixedWidth(400)
        self.right_frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-top-right-radius: 16px;
                border-bottom-right-radius: 16px;
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
                font-family: "{ff}";
            }}
        """)
        
        self.right_layout = QVBoxLayout(self.right_frame)
        self.right_layout.setContentsMargins(40, 40, 40, 40)
        
        self.stack = QStackedWidget(self.right_frame)
        self.right_layout.addWidget(self.stack)
        
        qss_lineedit = f"""
            QLineEdit {{
                border: 1px solid #e2e8f0; border-radius: 5px; padding: 8px 12px;
                background-color: #f7fafc; font-size: 14px; color: #1a202c; font-family: '{ff}';
            }}
            QLineEdit:focus {{ border: 1px solid #3182ce; background-color: #ffffff; }}
        """
        
        btn_hyperlink_qss = f"""
            QPushButton {{ background: transparent; border: none; color: #3182ce; text-align: left; font-size: 14px; font-family: '{ff}'; }}
            QPushButton:hover {{ text-decoration: underline; color: #2b6cb0; }}
        """
        
        btn_primary_qss = f"""
            QPushButton {{ background-color: #3182ce; color: white; border: none; border-radius: 5px; padding: 10px 15px; font-weight: bold; font-size: 14px; font-family: '{ff}'; }}
            QPushButton:hover {{ background-color: #2b6cb0; }}
            QPushButton:pressed {{ background-color: #2c5282; }}
            QPushButton:disabled {{ background-color: #a0aec0; }}
        """
        
        # -- Login Page --
        self.login_page = QWidget()
        login_page_layout = QVBoxLayout(self.login_page)
        login_page_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_id = QLabel("Email / ID")
        lbl_id.setStyleSheet(f"color: #4a5568; font-weight: bold; font-size: 14px; font-family: '{ff}';")
        self.login_id_input = QLineEdit()
        self.login_id_input.setPlaceholderText("name@example.com")
        self.login_id_input.setStyleSheet(qss_lineedit)
        
        lbl_pw = QLabel("Password")
        lbl_pw.setStyleSheet(f"color: #4a5568; font-weight: bold; font-size: 14px; font-family: '{ff}';")
        self.login_pw_input = QLineEdit()
        self.login_pw_input.setEchoMode(QLineEdit.Password)
        self.login_pw_input.setPlaceholderText("••••••••")
        self.login_pw_input.setStyleSheet(qss_lineedit)
        
        self.auto_login_cb = QCheckBox("자동 로그인 (Keep me signed in)")
        self.auto_login_cb.setStyleSheet(f"""
            QCheckBox {{ font-size: 14px; color: #4a5568; font-family: '{ff}'; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 3px; border: 1px solid #cbd5e0; background: white; }}
            QCheckBox::indicator:checked {{ background: #3182ce; border: 1px solid #3182ce; }}
        """)
        
        # Bottom row for login
        login_bottom_layout = QHBoxLayout()
        self.to_signup_btn = QPushButton("Don't have an account? Sign up")
        self.to_signup_btn.setCursor(Qt.PointingHandCursor)
        self.to_signup_btn.setAutoDefault(False)
        self.to_signup_btn.setStyleSheet(btn_hyperlink_qss)
        
        self.login_btn = QPushButton("Login")
        self.login_btn.setFixedWidth(100)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet(btn_primary_qss)
        
        self.to_signup_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.login_btn.clicked.connect(self.do_login)
        self.login_id_input.returnPressed.connect(self.do_login)
        self.login_pw_input.returnPressed.connect(self.do_login)
        
        login_bottom_layout.addWidget(self.to_signup_btn)
        login_bottom_layout.addStretch(1)
        login_bottom_layout.addWidget(self.login_btn)
        
        login_page_layout.addStretch(1)
        login_page_layout.addWidget(lbl_id)
        login_page_layout.addWidget(self.login_id_input)
        login_page_layout.addSpacing(15)
        login_page_layout.addWidget(lbl_pw)
        login_page_layout.addWidget(self.login_pw_input)
        login_page_layout.addSpacing(10)
        login_page_layout.addWidget(self.auto_login_cb)
        login_page_layout.addSpacing(30)
        login_page_layout.addLayout(login_bottom_layout)
        login_page_layout.addStretch(1)
        
        # -- Signup Page --
        self.signup_page = QWidget()
        signup_page_layout = QVBoxLayout(self.signup_page)
        signup_page_layout.setContentsMargins(0, 0, 0, 0)
        
        s_lbl_name = QLabel("성함 (Name)")
        s_lbl_name.setStyleSheet(f"color: #4a5568; font-weight: bold; font-size: 14px; font-family: '{ff}';")
        self.signup_name_input = QLineEdit()
        self.signup_name_input.setStyleSheet(qss_lineedit)
        
        s_lbl_id = QLabel("사용할 아이디 (ID)")
        s_lbl_id.setStyleSheet(f"color: #4a5568; font-weight: bold; font-size: 14px; font-family: '{ff}';")
        self.signup_id_input = QLineEdit()
        self.signup_id_input.setStyleSheet(qss_lineedit)
        
        s_lbl_pw = QLabel("비밀번호 (Password)")
        s_lbl_pw.setStyleSheet(f"color: #4a5568; font-weight: bold; font-size: 14px; font-family: '{ff}';")
        self.signup_pw_input = QLineEdit()
        self.signup_pw_input.setEchoMode(QLineEdit.Password)
        self.signup_pw_input.setStyleSheet(qss_lineedit)
        
        s_lbl_pw_conf = QLabel("비밀번호 확인 (Confirm)")
        s_lbl_pw_conf.setStyleSheet(f"color: #4a5568; font-weight: bold; font-size: 14px; font-family: '{ff}';")
        self.signup_pw_conf_input = QLineEdit()
        self.signup_pw_conf_input.setEchoMode(QLineEdit.Password)
        self.signup_pw_conf_input.setStyleSheet(qss_lineedit)
        
        # Bottom row for signup
        signup_bottom_layout = QHBoxLayout()
        self.to_login_btn = QPushButton("Already have an account? Login")
        self.to_login_btn.setCursor(Qt.PointingHandCursor)
        self.to_login_btn.setAutoDefault(False)
        self.to_login_btn.setStyleSheet(btn_hyperlink_qss)
        
        self.signup_btn = QPushButton("Create Account")
        self.signup_btn.setCursor(Qt.PointingHandCursor)
        self.signup_btn.setStyleSheet(btn_primary_qss)
        
        self.to_login_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.signup_btn.clicked.connect(self.do_signup)
        self.signup_id_input.returnPressed.connect(self.do_signup)
        self.signup_pw_input.returnPressed.connect(self.do_signup)
        self.signup_pw_conf_input.returnPressed.connect(self.do_signup)
        
        signup_bottom_layout.addWidget(self.to_login_btn)
        signup_bottom_layout.addStretch(1)
        signup_bottom_layout.addWidget(self.signup_btn)
        
        signup_page_layout.addStretch(1)
        signup_page_layout.addWidget(s_lbl_name)
        signup_page_layout.addWidget(self.signup_name_input)
        signup_page_layout.addSpacing(10)
        signup_page_layout.addWidget(s_lbl_id)
        signup_page_layout.addWidget(self.signup_id_input)
        signup_page_layout.addSpacing(10)
        signup_page_layout.addWidget(s_lbl_pw)
        signup_page_layout.addWidget(self.signup_pw_input)
        signup_page_layout.addSpacing(10)
        signup_page_layout.addWidget(s_lbl_pw_conf)
        signup_page_layout.addWidget(self.signup_pw_conf_input)
        signup_page_layout.addSpacing(20)
        signup_page_layout.addLayout(signup_bottom_layout)
        signup_page_layout.addStretch(1)
        
        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.signup_page)
        
        # Add Close button at top right
        close_btn = QPushButton("✕", self.right_frame)
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; border: none; font-size: 16px; color: #a0aec0; font-family: "{ff}"; }}
            QPushButton:hover {{ color: #e53e3e; }}
        """)
        close_btn.clicked.connect(self.reject)
        
        wrapper_layout.addWidget(self.left_frame)
        wrapper_layout.addWidget(self.right_frame)
        
        container_layout.addWidget(self.wrapper)
        main_layout.addWidget(self.container)
        
        # Position close button absolutely
        close_btn.move(self.right_frame.width() - 40, 10)

    def do_login(self):
        user_id = self.login_id_input.text().strip()
        pw = self.login_pw_input.text()
        
        if not user_id or not pw:
            QMessageBox.warning(self, "오류", "아이디와 비밀번호를 모두 입력해주세요.")
            return
            
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Logging in...")
        
        self.thread = LoginThread("login", user_id, pw)
        self.thread.success.connect(self.on_login_success)
        self.thread.error.connect(self.on_login_error)
        self.thread.start()

    def do_auto_login(self):
        saved_id = self.auto_login_data.get("saved_id")
        saved_pw_hash = self.auto_login_data.get("saved_pw")
        
        if saved_id and saved_pw_hash:
            self.thread = LoginThread("auto_login", saved_id, saved_pw_hash)
            self.thread.success.connect(self.on_login_success)
            self.thread.error.connect(self.on_auto_login_error)
            self.thread.start()

    def do_signup(self):
        name = self.signup_name_input.text().strip()
        user_id = self.signup_id_input.text().strip()
        pw = self.signup_pw_input.text()
        pw_conf = self.signup_pw_conf_input.text()
        
        if not all([name, user_id, pw, pw_conf]):
            QMessageBox.warning(self, "오류", "모든 항목을 입력해주세요.")
            return
            
        if pw != pw_conf:
            QMessageBox.warning(self, "오류", "비밀번호가 일치하지 않습니다.")
            return
            
        self.signup_btn.setEnabled(False)
        self.signup_btn.setText("Creating...")
        
        self.thread = LoginThread("signup", user_id, pw, name=name)
        self.thread.signup_success.connect(self.on_signup_success)
        self.thread.error.connect(self.on_signup_error)
        self.thread.start()

    def on_login_success(self, data):
        global SESSION
        SESSION["id"] = data["id"]
        SESSION["name"] = data["name"]
        
        if self.auto_login_cb.isChecked():
            hashed_pw = hashlib.sha256(self.login_pw_input.text().encode('utf-8')).hexdigest()
            self.save_settings(data["id"], hashed_pw, True)
        else:
            self.save_settings("", "", False)
            
        self.accept()

    def on_login_error(self, msg):
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Login")
        QMessageBox.warning(self, "로그인 실패", msg)

    def on_auto_login_error(self, msg):
        self.save_settings("", "", False)

    def on_signup_success(self, msg):
        self.signup_btn.setEnabled(True)
        self.signup_btn.setText("Create Account")
        QMessageBox.information(self, "성공", msg)
        self.stack.setCurrentIndex(0)
        self.login_id_input.setText(self.signup_id_input.text())
        self.login_pw_input.clear()
        
    def on_signup_error(self, msg):
        self.signup_btn.setEnabled(True)
        self.signup_btn.setText("Create Account")
        QMessageBox.warning(self, "회원가입 실패", msg)
