from src.utils.helpers import load_companies

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile
except ImportError:
    QWebEngineView = None
    QWebEnginePage = None
    QWebEngineProfile = None

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
from src.core.scraper_threads import StatsScraperWorker
from src.config import SESSION, WORKSPACE_DIR, ASSETS_DIR, DATA_DIR, FONT_DIR, SETTINGS_PATH, CREDENTIALS_PATH
from src.utils.helpers import safe_json_load

class IndexCheckInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("IndexCheckInterface")
        
        self.base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        self.companies = []
        self.worker = None
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(20)
        
        # Title
        title_label = TitleLabel("지수 체크 (블로그 통계 대시보드)", self)
        layout.addWidget(title_label)
        
        # Top Control Bar
        control_card = CardWidget(self)
        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(20, 16, 20, 16)
        control_layout.setSpacing(16)
        
        self.combo_lbl = QLabel("업체 선택:", control_card)
        self.combo_lbl.setFont(QFont("SUIT", 10, QFont.Bold))
        is_dark = isDarkTheme()
        self.combo_lbl.setStyleSheet(f"color: {'#FFFFFF' if is_dark else '#000000'}; background: transparent;")
        control_layout.addWidget(self.combo_lbl)
        
        self.company_combo = ComboBox(control_card)
        self.company_combo.setMinimumWidth(200)
        self.company_combo.currentIndexChanged.connect(self.on_company_changed)
        control_layout.addWidget(self.company_combo)
        
        self.update_btn = PushButton("통계 데이터 갱신", control_card)
        self.update_btn.setMinimumWidth(150)
        self.update_btn.clicked.connect(self.update_stats)
        control_layout.addWidget(self.update_btn)
        
        self.loading_ring = IndeterminateProgressRing(control_card)
        self.loading_ring.setFixedSize(24, 24)
        self.loading_ring.hide()
        control_layout.addWidget(self.loading_ring)
        
        self.status_label = QLabel(control_card)
        self.status_label.setFont(QFont("SUIT", 9))
        self.status_label.setStyleSheet("color: #AAAAAA; background: transparent;")
        control_layout.addWidget(self.status_label)
        
        control_layout.addStretch(1)
        
        self.time_label = QLabel("업데이트 기록 없음", control_card)
        self.time_label.setFont(QFont("SUIT", 9))
        self.time_label.setStyleSheet("color: #888888; background: transparent;")
        control_layout.addWidget(self.time_label)
        
        layout.addWidget(control_card)
        
        if QWebEngineView is None:
            error_lbl = SubtitleLabel("PyQtWebEngine 모듈이 설치되지 않아 차트를 렌더링할 수 없습니다.\n앱을 재시작하면 자동으로 설치됩니다.", self)
            layout.addWidget(error_lbl)
            layout.addStretch(1)
            return
            
        # WebEngineView for ECharts
        self.chart_view = QWebEngineView(self)
        self.chart_view.setStyleSheet("background: transparent; border-radius: 12px;")
        
        self.init_chart()
        layout.addWidget(self.chart_view, 1) # stretch 1
        
        qconfig.themeChanged.connect(self.update_chart_theme)
        
    def showEvent(self, event):
        super().showEvent(event)
        self.load_company_list()
        
    def load_company_list(self):
        prev_idx = self.company_combo.currentIndex()
        prev_text = self.company_combo.currentText()
        
        self.company_combo.blockSignals(True)
        self.company_combo.clear()
        self.companies = load_companies()
        
        for comp in self.companies:
            name = comp.get('name', '이름 없음')
            self.company_combo.addItem(name)
            
        self.company_combo.blockSignals(False)
        
        # Restore previous selection if possible
        if prev_text:
            idx = self.company_combo.findText(prev_text)
            if idx >= 0:
                self.company_combo.setCurrentIndex(idx)
            else:
                self.company_combo.setCurrentIndex(0 if self.companies else -1)
        else:
            self.company_combo.setCurrentIndex(0 if self.companies else -1)
            
        # Force refresh data trigger
        self.on_company_changed(self.company_combo.currentIndex())
        
    def on_company_changed(self, index):
        if index < 0 or index >= len(self.companies):
            self.clear_chart()
            self.time_label.setText("업체 정보가 없습니다.")
            return
            
        company_data = self.companies[index]
        company_name = company_data.get('name', '')
        
        # Load local stats JSON file
        stats_path = os.path.join(self.base_dir, "Data", f"stats_{company_name}.json")
        stats_data = safe_json_load(stats_path, default=None)
        if stats_data:
            self.time_label.setText(f"최근 업데이트: {stats_data.get('last_updated', '알 수 없음')}")
            self.render_stats(stats_data)
        else:
            self.time_label.setText("통계 데이터가 없거나 업데이트를 진행해 주세요.")
            self.clear_chart()
            
    def render_stats(self, stats_data):
        if not hasattr(self, 'chart_view'): return
        
        dates = stats_data.get('dates', [])
        visitor = stats_data.get('visitor', [])
        views = stats_data.get('views', [])
        inflow = stats_data.get('inflow', [])
        
        js_code = f"updateData({json.dumps(dates)}, {json.dumps(visitor)}, {json.dumps(views)}, {json.dumps(inflow)});"
        self.chart_view.page().runJavaScript(js_code)
        
    def clear_chart(self):
        if not hasattr(self, 'chart_view'): return
        js_code = "updateData([], [], [], []);"
        self.chart_view.page().runJavaScript(js_code)
        
    def update_stats(self):
        index = self.company_combo.currentIndex()
        if index < 0 or index >= len(self.companies):
            return
            
        company_data = self.companies[index]
        company_name = company_data.get('name', '')
        blog_id = company_data.get('blog_id', '').strip()
        
        if not blog_id:
            MessageBox("알림", "해당 업체의 네이버 블로그 ID가 설정되어 있지 않습니다.\n'업체 리스트' 탭에서 [수정]을 통해 블로그 ID를 먼저 등록해 주세요.", self).exec_()
            return
            
        # Get global driver path from scraper interface if available
        driver_path = ""
        if hasattr(self.parent(), 'scraper_interface'):
            driver_path = self.parent().scraper_interface.global_driver_path
            
        # UI update to loading state
        self.company_combo.setEnabled(False)
        self.update_btn.setEnabled(False)
        self.loading_ring.show()
        self.loading_ring.start()
        self.status_label.setText("크롬 드라이버 준비 중...")
        
        self.worker = StatsScraperWorker(blog_id, company_name, driver_path)
        self.worker.status.connect(self.on_worker_status)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.error.connect(self.on_worker_error)
        self.worker.start()
        
    def on_worker_status(self, msg):
        self.status_label.setText(msg)
        
    def on_worker_finished(self, stats_data):
        self.company_combo.setEnabled(True)
        self.update_btn.setEnabled(True)
        self.loading_ring.stop()
        self.loading_ring.hide()
        self.status_label.setText("데이터 업데이트 성공!")
        self.time_label.setText(f"최근 업데이트: {stats_data.get('last_updated', '')}")
        self.render_stats(stats_data)
        InfoBar.success("성공", f"'{self.company_combo.currentText()}' 블로그 통계 수집이 완료되었습니다.", duration=3000, parent=self)
        
    def on_worker_error(self, err_msg):
        self.company_combo.setEnabled(True)
        self.update_btn.setEnabled(True)
        self.loading_ring.stop()
        self.loading_ring.hide()
        self.status_label.setText("실패")
        MessageBox("오류 발생", f"통계 데이터 수집 중 오류가 발생했습니다:\n{err_msg}", self).exec_()
        
    def init_chart(self):
        is_dark = isDarkTheme()
        theme_str = 'dark' if is_dark else 'light'
        bg_color = '#202020' if is_dark else '#F3F3F3'
        card_bg = '#2C2C2C' if is_dark else '#FFFFFF'
        border_color = '#3A3A3A' if is_dark else '#E5E5E5'
        text_color = '#FFFFFF' if is_dark else '#000000'
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
            <style>
                html, body {{
                    margin: 0;
                    padding: 0;
                    width: 100%;
                    height: 100%;
                    background-color: {bg_color};
                    overflow: hidden;
                    border-radius: 12px;
                }}
                .container {{
                    display: flex;
                    width: 100%;
                    height: 100%;
                    box-sizing: border-box;
                    padding: 20px;
                    gap: 24px;
                }}
                #main {{
                    flex: 2;
                    height: 100%;
                    background-color: {card_bg};
                    border-radius: 12px;
                    border: 1px solid {border_color};
                }}
                #inflow {{
                    flex: 1;
                    height: 100%;
                    background-color: {card_bg};
                    border-radius: 12px;
                    border: 1px solid {border_color};
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div id="main"></div>
                <div id="inflow"></div>
            </div>
            <script type="text/javascript">
                var currentTheme = '{theme_str}';
                var textCol = '{text_color}';
                var mainChart = echarts.init(document.getElementById('main'), currentTheme);
                var inflowChart = echarts.init(document.getElementById('inflow'), currentTheme);
                
                var mainOption = {{
                    backgroundColor: 'transparent',
                    title: {{
                        text: '방문자수 및 조회수 추이 (최근 30일)',
                        textStyle: {{ color: textCol, fontFamily: 'SUIT, sans-serif', fontSize: 16 }},
                        left: '5%',
                        top: 20
                    }},
                    tooltip: {{
                        trigger: 'axis',
                        axisPointer: {{ type: 'cross' }}
                    }},
                    legend: {{
                        data: ['방문자수', '조회수'],
                        top: 20,
                        right: '5%',
                        textStyle: {{ color: textCol, fontFamily: 'SUIT, sans-serif' }}
                    }},
                    grid: {{
                        left: '5%',
                        right: '5%',
                        bottom: '10%',
                        top: '20%',
                        containLabel: true
                    }},
                    xAxis: [{{
                        type: 'category',
                        boundaryGap: false,
                        data: [],
                        axisLine: {{ lineStyle: {{ color: textCol, opacity: 0.5 }} }},
                        axisLabel: {{ fontFamily: 'SUIT, sans-serif', color: textCol }}
                    }}],
                    yAxis: [{{
                        type: 'value',
                        axisLine: {{ lineStyle: {{ color: textCol, opacity: 0.5 }} }},
                        splitLine: {{ lineStyle: {{ color: textCol, opacity: 0.1 }} }},
                        axisLabel: {{ fontFamily: 'SUIT, sans-serif', color: textCol }}
                    }}],
                    series: [
                        {{
                            name: '방문자수',
                            type: 'line',
                            smooth: true,
                            lineStyle: {{ width: 4, color: '#0078D4' }},
                            itemStyle: {{ color: '#0078D4' }},
                            areaStyle: {{
                                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                    {{ offset: 0, color: 'rgba(0, 120, 212, 0.3)' }},
                                    {{ offset: 1, color: 'rgba(0, 120, 212, 0.0)' }}
                                    ])
                            }},
                            data: []
                        }},
                        {{
                            name: '조회수',
                            type: 'line',
                            smooth: true,
                            lineStyle: {{ width: 4, color: '#25A662' }},
                            itemStyle: {{ color: '#25A662' }},
                            areaStyle: {{
                                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                    {{ offset: 0, color: 'rgba(37, 166, 98, 0.3)' }},
                                    {{ offset: 1, color: 'rgba(37, 166, 98, 0.0)' }}
                                    ])
                            }},
                            data: []
                        }}
                    ]
                }};
                
                var inflowOption = {{
                    backgroundColor: 'transparent',
                    title: {{
                        text: '유입 경로 분석 (Top 5)',
                        textStyle: {{ color: textCol, fontFamily: 'SUIT, sans-serif', fontSize: 16 }},
                        left: 'center',
                        top: 20
                    }},
                    tooltip: {{
                        trigger: 'item',
                        formatter: '{{b}}: {{c}} ({{d}}%)'
                    }},
                    legend: {{
                        bottom: 15,
                        left: 'center',
                        textStyle: {{ color: textCol, fontFamily: 'SUIT, sans-serif', fontSize: 11 }}
                    }},
                    series: [{{
                        name: '유입 수',
                        type: 'pie',
                        radius: ['35%', '60%'],
                        center: ['50%', '45%'],
                        avoidLabelOverlap: false,
                        itemStyle: {{
                            borderRadius: 8,
                            borderColor: '{card_bg}',
                            borderWidth: 2
                        }},
                        label: {{ show: false }},
                        data: []
                    }}]
                }};
                
                mainChart.setOption(mainOption);
                inflowChart.setOption(inflowOption);
                
                window.onresize = function() {{
                    mainChart.resize();
                    inflowChart.resize();
                }};
                
                function updateData(dates, visitor, views, inflow) {{
                    mainOption.xAxis[0].data = dates;
                    mainOption.series[0].data = visitor;
                    mainOption.series[1].data = views;
                    mainChart.setOption(mainOption);
                    
                    inflowOption.series[0].data = inflow;
                    inflowChart.setOption(inflowOption);
                }}
                
                function updateTheme(newTheme, newBgColor, newCardBg, newBorderColor, newTextColor) {{
                    mainChart.dispose();
                    inflowChart.dispose();
                    
                    document.body.style.backgroundColor = newBgColor;
                    
                    var divs = document.querySelectorAll('#main, #inflow');
                    divs.forEach(function(d) {{
                        d.style.backgroundColor = newCardBg;
                        d.style.borderColor = newBorderColor;
                    }});
                    
                    currentTheme = newTheme;
                    textCol = newTextColor;
                    
                    mainChart = echarts.init(document.getElementById('main'), currentTheme);
                    inflowChart = echarts.init(document.getElementById('inflow'), currentTheme);
                    
                    mainOption.title.textStyle.color = textCol;
                    mainOption.legend.textStyle.color = textCol;
                    mainOption.xAxis[0].axisLine.lineStyle.color = textCol;
                    mainOption.xAxis[0].axisLabel.color = textCol;
                    mainOption.yAxis[0].axisLine.lineStyle.color = textCol;
                    mainOption.yAxis[0].splitLine.lineStyle.color = textCol;
                    mainOption.yAxis[0].axisLabel.color = textCol;
                    mainChart.setOption(mainOption);
                    
                    inflowOption.title.textStyle.color = textCol;
                    inflowOption.legend.textStyle.color = textCol;
                    inflowOption.series[0].itemStyle.borderColor = newCardBg;
                    inflowChart.setOption(inflowOption);
                }}
            </script>
        </body>
        </html>
        """
        self.chart_view.setHtml(html)
        
    def update_chart_theme(self):
        if not hasattr(self, 'chart_view'): return
        is_dark = isDarkTheme()
        theme_str = 'dark' if is_dark else 'light'
        bg_color = '#202020' if is_dark else '#F3F3F3'
        card_bg = '#2C2C2C' if is_dark else '#FFFFFF'
        border_color = '#3A3A3A' if is_dark else '#E5E5E5'
        text_color = '#FFFFFF' if is_dark else '#000000'
        
        js_code = f"updateTheme('{theme_str}', '{bg_color}', '{card_bg}', '{border_color}', '{text_color}');"
        self.chart_view.page().runJavaScript(js_code)
        
        if hasattr(self, 'combo_lbl'):
            self.combo_lbl.setStyleSheet(f"color: {text_color}; background: transparent;")

