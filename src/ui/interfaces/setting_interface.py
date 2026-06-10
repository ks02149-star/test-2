from src.utils.helpers import check_for_updates

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
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, FONT_DIR, SETTINGS_PATH, CREDENTIALS_PATH, VERSION

class SettingInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingInterface")
        
        # Scroll Area configuration
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_content.setStyleSheet("QWidget#ScrollContent { background: transparent; }")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(36, 36, 36, 36)
        
        self.setWidget(self.scroll_content)
        
        # Title
        self.title_label = TitleLabel("설정", self.scroll_content)
        self.scroll_layout.addWidget(self.title_label)
        self.scroll_layout.addSpacing(20)
        
        # Update Card
        self.update_card = CardWidget(self.scroll_content)
        self.update_layout = QHBoxLayout(self.update_card)
        self.update_layout.setContentsMargins(20, 20, 20, 20)
        
        self.version_info = BodyLabel(f"현재 버전: v{VERSION}", self.update_card)
        self.update_btn = PrimaryPushButton("업데이트 확인", self.update_card)
        self.update_btn.clicked.connect(lambda: check_for_updates(manual_check=True))
        
        self.update_layout.addWidget(self.version_info)
        self.update_layout.addStretch(1)
        self.update_layout.addWidget(self.update_btn)
        
        self.scroll_layout.addWidget(self.update_card)
        self.scroll_layout.addStretch(1)

