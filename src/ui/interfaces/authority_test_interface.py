from PyQt5.QtWidgets import QVBoxLayout, QLabel, QWidget
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QTimer, Qt
from qfluentwidgets import ScrollArea, MessageBox
from src.config import SESSION

class AuthorityTestInterface(ScrollArea):
    def __init__(self, main_window, parent=None):
        super().__init__(parent=parent)
        self.main_window = main_window
        self.setObjectName("AuthorityTestInterface")
        
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        
        self.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            #AuthorityTestInterface { background: transparent; }
        """)
        
        self.layout = QVBoxLayout(self.view)
        self.layout.setAlignment(Qt.AlignCenter)
        
        self.title_label = QLabel("관리자 권한 확인 완료")
        self.title_label.setFont(QFont("SUIT", 24, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: white;")
        
        self.sub_label = QLabel("관리자로 로그인하셨습니다. 모든 기능에 접근 가능합니다.")
        self.sub_label.setFont(QFont("SUIT", 14))
        self.sub_label.setAlignment(Qt.AlignCenter)
        self.sub_label.setStyleSheet("color: #a0aec0;")
        
        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.sub_label)

    def showEvent(self, e):
        super().showEvent(e)
        if not SESSION.get("is_admin", False):
            self.title_label.hide()
            self.sub_label.hide()
            self.view.setStyleSheet("background-color: black;")
            # QTimer prevents blocking the showEvent and allows UI to update before showing popup
            QTimer.singleShot(0, self.show_error_and_redirect)
        else:
            self.title_label.show()
            self.sub_label.show()
            self.view.setStyleSheet("background-color: transparent;")
            
    def show_error_and_redirect(self):
        msg_box = MessageBox("권한 오류", "접근 권한이 없습니다. 관리자에게 문의하세요.", self.window())
        msg_box.exec_()
        self.main_window.switchTo(self.main_window.home_interface)
