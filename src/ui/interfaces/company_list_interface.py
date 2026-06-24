from src.utils.helpers import load_companies, save_companies

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
from src.ui.components.dialogs import CompanyDialog
from src.ui.components.cards import CompanyCard
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, FONT_DIR, SETTINGS_PATH, CREDENTIALS_PATH

class CompanyListInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("CompanyListInterface")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 36, 36, 36)
        main_layout.setSpacing(16)
        
        # Header (Title + Buttons)
        header_layout = QHBoxLayout()
        self.title_label = TitleLabel("업체 리스트", self)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch(1)
        
        self.add_btn = PushButton("업체 추가", self)
        self.add_btn.setIcon(FluentIcon.ADD)
        self.add_btn.clicked.connect(self.add_company)
        header_layout.addWidget(self.add_btn)
        
        main_layout.addLayout(header_layout)
        
        # Content layout (Split layout)
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(24)
        
        # Left Panel: Scroll Area for Card List
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_content.setStyleSheet("QWidget#ScrollContent { background: transparent; }")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 10, 0)
        self.scroll_layout.setSpacing(16)
        
        self.scroll_area.setWidget(self.scroll_content)
        self.content_layout.addWidget(self.scroll_area, 1)
        
        main_layout.addLayout(self.content_layout, 1)
        
        # Load and render initial list
        self.companies = load_companies()
        self.render_list()
        
    def render_list(self):
        # Clear existing layout
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # Create a card for each company
        for idx, company in enumerate(self.companies):
            card = CompanyCard(
                company, 
                on_edit=lambda checked, i=idx: self.edit_company(i),
                on_delete=lambda checked, i=idx: self.delete_company(i),
                parent=self.scroll_content
            )
            self.scroll_layout.addWidget(card)
            
        self.scroll_layout.addStretch(1)

    def add_company(self):
        dialog = CompanyDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_data()
            self.companies.append(new_data)
            save_companies(self.companies)
            self.render_list()
            InfoBar.success("성공", f"'{new_data['name']}' 업체가 추가되었습니다.", duration=3000, parent=self)
            
    def edit_company(self, index):
        if index < 0 or index >= len(self.companies):
            return
        company_data = self.companies[index]
        dialog = CompanyDialog(company_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_data()
            self.companies[index] = updated_data
            save_companies(self.companies)
            self.render_list()
            InfoBar.success("성공", f"'{updated_data['name']}' 업체 정보가 수정되었습니다.", duration=3000, parent=self)
            
    def delete_company(self, index):
        if index < 0 or index >= len(self.companies):
            return
        company_name = self.companies[index].get('name', '이름 없음')
        
        w = MessageBox('업체 삭제', f"'{company_name}' 업체를 삭제하시겠습니까?", self)
        if w.exec_():
            self.companies.pop(index)
            save_companies(self.companies)
            self.render_list()
            InfoBar.success("성공", f"'{company_name}' 업체가 삭제되었습니다.", duration=3000, parent=self)

