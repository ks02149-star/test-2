
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
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, FONT_DIR, SETTINGS_PATH, CREDENTIALS_PATH

class HomeViewWidget(QWidget):
    def __init__(self, bg_path, parent=None):
        super().__init__(parent)
        self.bg_pixmap = QPixmap(bg_path)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        if self.parentWidget() and not self.bg_pixmap.isNull():
            viewport_size = self.parentWidget().size()
            scaled_pixmap = self.bg_pixmap.scaled(viewport_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            x_offset = (viewport_size.width() - scaled_pixmap.width()) // 2
            y_offset = (viewport_size.height() - scaled_pixmap.height()) // 2
            
            scroll_x = -self.x()
            scroll_y = -self.y()
            
            painter.drawPixmap(scroll_x + x_offset, scroll_y + y_offset, scaled_pixmap)
        else:
            super().paintEvent(event)

