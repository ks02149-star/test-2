from src.utils.helpers import load_companies

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile
except ImportError as e:
    import traceback
    with open("webengine_import_error.log", "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
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
from src.utils.helpers import safe_json_load, safe_json_save

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
        title_label = TitleLabel("블로그 통계 대시보드", self)
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
        
        self.month_lbl = QLabel("조회 월:", control_card)
        self.month_lbl.setFont(QFont("SUIT", 10, QFont.Bold))
        self.month_lbl.setStyleSheet(f"color: {'#FFFFFF' if is_dark else '#000000'}; background: transparent;")
        control_layout.addWidget(self.month_lbl)
        
        self.month_combo = ComboBox(control_card)
        self.month_combo.setMinimumWidth(120)
        self.month_combo.currentIndexChanged.connect(self.on_month_changed)
        control_layout.addWidget(self.month_combo)
        
        self.update_btn = PushButton("통계 데이터 갱신", control_card)
        self.update_btn.setMinimumWidth(150)
        self.update_btn.clicked.connect(self.update_stats)
        control_layout.addWidget(self.update_btn)
        
        self.export_btn = PushButton("이미지 내보내기", control_card)
        self.export_btn.clicked.connect(self.export_image)
        control_layout.addWidget(self.export_btn)
        
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
            error_lbl = SubtitleLabel("PyQtWebEngine 모듈을 로드할 수 없어 차트를 렌더링할 수 없습니다.\n문제가 지속될 경우 관리자에게 문의하세요.", self)
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
            self.current_stats_data = {}
            self.month_combo.blockSignals(True)
            self.month_combo.clear()
            self.month_combo.blockSignals(False)
            self.clear_chart()
            self.time_label.setText("업체 정보가 없습니다.")
            return
            
        company_data = self.companies[index]
        company_name = company_data.get('name', '')
        
        # Load local stats JSON file
        stats_path = os.path.join(self.base_dir, "Data", f"stats_{company_name}.json")
        stats_data = safe_json_load(stats_path, default=None)
        
        if stats_data:
            # Migration logic if missing 'history'
            if 'history' not in stats_data:
                old_data = stats_data.copy()
                stats_data = {'history': {}, 'last_updated': old_data.get('last_updated', '')}
                if 'dates' in old_data and old_data['dates']:
                    stats_data['history'][old_data['dates'][-1]] = old_data
                    
            self.current_stats_data = stats_data
            self.time_label.setText(f"최근 업데이트: {stats_data.get('last_updated', '알 수 없음')}")
            
            self.month_combo.blockSignals(True)
            self.month_combo.clear()
            history = stats_data.get('history', {})
            months = sorted(history.keys())
            for m in months:
                self.month_combo.addItem(m)
            if months:
                self.month_combo.setCurrentIndex(len(months) - 1)
            self.month_combo.blockSignals(False)
            self.on_month_changed(self.month_combo.currentIndex())
        else:
            self.current_stats_data = {}
            self.month_combo.blockSignals(True)
            self.month_combo.clear()
            self.month_combo.blockSignals(False)
            self.time_label.setText("통계 데이터가 없거나 업데이트를 진행해 주세요.")
            self.clear_chart()
            
    def on_month_changed(self, index):
        if index < 0 or not hasattr(self, 'current_stats_data'):
            self.clear_chart()
            return
            
        month = self.month_combo.itemText(index)
        history = self.current_stats_data.get('history', {})
        target_stats = history.get(month, {})
        
        if target_stats:
            self.render_stats(target_stats)
        else:
            self.clear_chart()
            
    def render_stats(self, stats_data):
        if not hasattr(self, 'chart_view'): return
        
        dates = stats_data.get('dates', [])
        views = stats_data.get('views', [])
        avg_time = stats_data.get('avg_time', {'my': 0, 'total': 0, 'top': 0, 'max': 0})
        inflow = stats_data.get('inflow', [])
        
        # '기타' 항목이 있다면 리스트의 가장 마지막으로 이동
        others = None
        for i, item in enumerate(inflow):
            if item.get('name') == '기타':
                others = inflow.pop(i)
                break
        if others:
            inflow.append(others)
        rank_posts = stats_data.get('rank_posts', [])
        visit_table = stats_data.get('visit_table', [])
        
        js_code = f"updateData({json.dumps(dates)}, {json.dumps(views)}, {json.dumps(avg_time)}, {json.dumps(inflow)}, {json.dumps(rank_posts)}, {json.dumps(visit_table)});"
        self.chart_view.page().runJavaScript(js_code)
        
    def clear_chart(self):
        if not hasattr(self, 'chart_view'): return
        js_code = "updateData([], [], {'my': 0, 'total': 0, 'top': 0, 'max': 0}, [], [], []);"
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
        self.month_combo.setEnabled(False)
        self.export_btn.setEnabled(False)
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
        self.month_combo.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.loading_ring.stop()
        self.loading_ring.hide()
        self.status_label.setText("데이터 업데이트 성공!")
        
        company_name = self.company_combo.currentText()
        stats_path = os.path.join(self.base_dir, "Data", f"stats_{company_name}.json")
        existing_data = safe_json_load(stats_path, default={'history': {}})
        
        if 'history' not in existing_data:
            old_data = existing_data.copy()
            existing_data = {'history': {}}
            if 'dates' in old_data and old_data['dates']:
                existing_data['history'][old_data['dates'][-1]] = old_data
                
        dates = stats_data.get('dates', [])
        if dates:
            target_month = dates[-1]
            existing_data['history'][target_month] = stats_data
            existing_data['last_updated'] = stats_data.get('last_updated', '')
            safe_json_save(stats_path, existing_data)
            self.current_stats_data = existing_data
            
            self.month_combo.blockSignals(True)
            self.month_combo.clear()
            history = existing_data.get('history', {})
            months = sorted(history.keys())
            for m in months:
                self.month_combo.addItem(m)
            if months:
                self.month_combo.setCurrentIndex(len(months) - 1)
            self.month_combo.blockSignals(False)
            self.on_month_changed(self.month_combo.currentIndex())
            
        self.time_label.setText(f"최근 업데이트: {existing_data.get('last_updated', '')}")
        InfoBar.success("성공", f"'{company_name}' 블로그 통계 수집이 완료되었습니다.", duration=3000, parent=self)
        
    def on_worker_error(self, err_msg):
        self.company_combo.setEnabled(True)
        self.update_btn.setEnabled(True)
        self.month_combo.setEnabled(True)
        self.export_btn.setEnabled(True)
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
                    margin: 0; padding: 0; width: 100%; height: 100%;
                    background-color: {bg_color}; overflow-y: auto; overflow-x: hidden;
                    border-radius: 12px; font-family: 'SUIT', sans-serif;
                }}
                /* Scrollbar styling */
                ::-webkit-scrollbar {{ width: 8px; }}
                ::-webkit-scrollbar-track {{ background: transparent; }}
                ::-webkit-scrollbar-thumb {{ background: rgba(150, 150, 150, 0.4); border-radius: 4px; }}
                ::-webkit-scrollbar-thumb:hover {{ background: rgba(150, 150, 150, 0.6); }}
                
                .dashboard {{
                    display: flex; flex-direction: column; width: 100%; min-height: 100%;
                    padding: 20px; box-sizing: border-box;
                }}
                .dashboard > div {{ margin-bottom: 20px; }}
                .dashboard > div:last-child {{ margin-bottom: 0; }}
                
                .summary-cards {{ display: flex; height: 140px; flex-shrink: 0; }}
                .summary-cards > .card {{ margin-right: 20px; }}
                .summary-cards > .card:last-child {{ margin-right: 0; }}
                .card {{
                    flex: 1; background-color: {card_bg}; border: 1px solid {border_color};
                    border-radius: 12px; display: flex; flex-direction: column;
                    padding: 24px; box-sizing: border-box; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                }}
                .card-title {{ color: {text_color}; opacity: 0.7; font-size: 14px; font-weight: bold; }}
                .card-value {{ color: {text_color}; font-size: 34px; font-weight: 800; margin-top: 6px; }}
                
                .chart-container {{
                    height: 380px; flex-shrink: 0; background-color: {card_bg};
                    border: 1px solid {border_color}; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                }}
                
                .tables-container {{ display: flex; flex: 1; min-height: 300px; }}
                .tables-container > .table-box {{ margin-right: 20px; }}
                .tables-container > .table-box:last-child {{ margin-right: 0; }}
                .table-box {{
                    flex: 1; background-color: {card_bg}; border: 1px solid {border_color};
                    border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                    display: flex; flex-direction: column;
                }}
                .table-box h3 {{ margin-top: 0; margin-bottom: 16px; color: {text_color}; font-size: 16px; font-weight: bold; }}
                
                .table-wrapper {{ overflow-y: auto; flex: 1; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{
                    text-align: left; padding: 12px 8px; border-bottom: 1px solid {border_color};
                    color: {text_color}; font-size: 13px;
                }}
                th {{ opacity: 0.6; font-weight: bold; position: sticky; top: 0; background-color: {card_bg}; z-index: 1; }}
                tr:last-child td {{ border-bottom: none; }}
                tr:hover td {{ background-color: rgba(150,150,150,0.1); }}
                
                /* Title ellipsis */
                .ellipsis {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 250px; display: inline-block; vertical-align: bottom; }}
                
                /* Export Mode - fits everything into 1000x560 using 2-column Grid */
                body.export-mode {{ overflow: hidden; border-radius: 0 !important; }}
                body.export-mode .dashboard {{ 
                    display: grid; 
                    grid-template-columns: 55fr 45fr; 
                    grid-template-rows: 80px 1fr auto; 
                    gap: 15px; 
                    height: 100vh; 
                    padding: 15px; 
                    box-sizing: border-box; 
                }}
                body.export-mode .dashboard > div {{ margin-bottom: 0; }}
                body.export-mode .summary-cards {{ grid-column: 1; grid-row: 1; height: 100%; }}
                body.export-mode .chart-container {{ grid-column: 1; grid-row: 2; height: 100%; }}
                body.export-mode .dashboard > .table-box {{ grid-column: 1; grid-row: 3; height: auto; }}
                body.export-mode .tables-container {{ grid-column: 2; grid-row: 1 / 4; display: flex; flex-direction: column; gap: 15px; min-height: 0; }}
                body.export-mode .tables-container > .table-box {{ flex: 1; margin-right: 0; display: flex; flex-direction: column; }}
                
                body.export-mode .card {{ padding: 12px 20px; }}
                body.export-mode .card-title {{ font-size: 12px; }}
                body.export-mode .card-value {{ font-size: 24px; margin-top: 4px; }}
                body.export-mode .table-box {{ padding: 12px 16px; }}
                body.export-mode .table-box h3 {{ margin-bottom: 8px; font-size: 13px; }}
                body.export-mode th, body.export-mode td {{ padding: 4px 6px; font-size: 11px; font-weight: 600; }}
                
                body.export-mode #val-time-inner {{ width: 100% !important; margin: 0px 0 0 0 !important; }}
                body.export-mode #val-time-inner .val-bar {{ top: 20px !important; }}
                body.export-mode #val-time-inner .val-circle {{ top: 28px !important; }}
                body.export-mode #val-time-inner .val-zero-text,
                body.export-mode #val-time-inner .val-my-text,
                body.export-mode #val-time-inner .val-max-text {{ top: -2px !important; }}
                body.export-mode #val-time-inner .val-bar-line {{ top: 10px !important; height: 30px !important; }}
                
                .label-export {{ display: none; }}
                body.export-mode .label-normal {{ display: none !important; }}
                body.export-mode .label-export {{ display: block !important; position: absolute; font-size: 12px; white-space: nowrap; font-weight: bold; top: -2px !important; }}
                
                .label-export-topright {{ display: none; }}
                body.export-mode .label-export-topright {{ display: block !important; position: absolute; right: 20px; top: 12px; font-size: 12px; font-weight: bold; color: #5C80F8; }}
                
                body.export-mode .tables-container > .table-box:first-child {{ margin-bottom: 15px; }}
                
                body.export-mode #tbody-inflow tr:nth-child(n+8) {{ display: none; }}
                body.export-mode #tbody-rank tr:nth-child(n+8) {{ display: none; }}
            </style>
        </head>
        <body>
            <div class="dashboard">
                <div class="summary-cards">
                    <div class="card">
                        <div class="card-title">최근 조회수 (마지막 월 기준)</div>
                        <div class="card-value" id="val-views">0</div>
                    </div>
                    <div class="card" style="flex: 2; position: relative;">
                        <div class="card-title">게시글 평균사용시간 (최근 월 기준)</div>
                        <div id="top-group-export-label" class="label-export-topright"></div>
                        <div id="val-time-container"></div>
                    </div>
                </div>
                <div class="chart-container" id="main"></div>
                <div class="table-box">
                    <div class="table-wrapper">
                        <table style="text-align: center;">
                            <thead><tr><th style="text-align:center;">기간</th><th style="text-align:center;">전체</th><th style="text-align:center;">피이웃</th><th style="text-align:center;">서로이웃</th><th style="text-align:center;">기타</th></tr></thead>
                            <tbody id="tbody-visit"></tbody>
                        </table>
                    </div>
                </div>
                <div class="tables-container">
                    <div class="table-box">
                        <h3 id="inflow-title">검색 유입 분석 TOP 10</h3>
                        <div class="table-wrapper">
                            <table>
                                <thead><tr><th>순위</th><th>유입 경로 / 키워드</th><th>비율(%)</th><th>조회수</th></tr></thead>
                                <tbody id="tbody-inflow"></tbody>
                            </table>
                        </div>
                    </div>
                    <div class="table-box">
                        <h3 id="rank-title">게시물 조회수 순위 TOP 10</h3>
                        <div class="table-wrapper">
                            <table>
                                <thead><tr><th>순위</th><th>게시물 제목</th><th>조회수</th></tr></thead>
                                <tbody id="tbody-rank"></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            <script type="text/javascript">
                var currentTheme = '{theme_str}';
                var textCol = '{text_color}';
                var cardBg = '{card_bg}';
                var borderColor = '{border_color}';
                var mainChart = echarts.init(document.getElementById('main'), currentTheme);
                
                var mainOption = {{
                    backgroundColor: 'transparent',
                    title: {{
                        text: '월간 조회수 추이',
                        textStyle: {{ color: textCol, fontFamily: 'SUIT, sans-serif', fontSize: 16 }},
                        left: 20, top: 20
                    }},
                    tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'cross' }} }},
                    legend: {{
                        data: ['조회수'], top: 20, right: 20,
                        textStyle: {{ color: textCol, fontFamily: 'SUIT, sans-serif' }}
                    }},
                    grid: {{ left: '3%', right: '4%', bottom: '5%', top: '25%', containLabel: true }},
                    xAxis: [{{
                        type: 'category', boundaryGap: false, data: [],
                        axisLine: {{ lineStyle: {{ color: textCol, opacity: 0.3 }} }},
                        axisLabel: {{ fontFamily: 'SUIT, sans-serif', color: textCol }}
                    }}],
                    yAxis: [{{
                        type: 'value',
                        axisLine: {{ show: false }},
                        splitLine: {{ lineStyle: {{ color: textCol, opacity: 0.1 }} }},
                        axisLabel: {{ fontFamily: 'SUIT, sans-serif', color: textCol }}
                    }}],
                    series: [
                        {{
                            name: '조회수', type: 'line', smooth: true,
                            lineStyle: {{ width: 4, color: '#0078D4' }},
                            itemStyle: {{ color: '#0078D4' }},
                            areaStyle: {{
                                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                    {{ offset: 0, color: 'rgba(0, 120, 212, 0.4)' }},
                                    {{ offset: 1, color: 'rgba(0, 120, 212, 0.0)' }}
                                ])
                            }},
                            data: []
                        }}
                    ]
                }};
                
                mainChart.setOption(mainOption);
                window.onresize = function() {{ mainChart.resize(); }};
                
                function updateData(dates, views, avg_time, inflow, rank_posts, visit_table) {{
                    mainOption.xAxis[0].data = dates;
                    mainOption.series[0].data = views;
                    mainChart.setOption(mainOption);
                    
                    // Render visit_table
                    let tbody_visit = document.getElementById('tbody-visit');
                    if (visit_table && visit_table.length > 0) {{
                        let rows = '';
                        for (let item of visit_table) {{
                            rows += `<tr>
                                <td style="text-align:center;">${{item.period}}</td>
                                <td style="text-align:center;">${{item.total}}</td>
                                <td style="text-align:center;">${{item.peer}}</td>
                                <td style="text-align:center;">${{item.mutual}}</td>
                                <td style="text-align:center;">${{item.other}}</td>
                            </tr>`;
                        }}
                        tbody_visit.innerHTML = rows;
                    }} else {{
                        tbody_visit.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px;">데이터가 없습니다.</td></tr>';
                    }}
                    
                    let my = avg_time.my || 0;
                    let total = avg_time.total || 0;
                    let top = avg_time.top || 0;
                    
                    let exportLabel = document.getElementById('top-group-export-label');
                    if (exportLabel) {{
                        exportLabel.innerText = top > 0 ? `상위 그룹 평균 ${{top}}` : '';
                    }}

                    let max = avg_time.max || 100;
                    if (max === 0) max = Math.max(my, total, top, 1);
                    
                    let meaningful_max = Math.max(my, total, top);
                    if (meaningful_max === 0) meaningful_max = 1;
                    
                    let is_broken = max > meaningful_max * 1.5;
                    let my_pct, total_pct, top_pct;
                    let broken_threshold = 82; // 82% width for the meaningful part
                    
                    if (is_broken) {{
                        let scale_max = meaningful_max * 1.2;
                        my_pct = Math.min((my / scale_max) * broken_threshold, broken_threshold);
                        total_pct = Math.min((total / scale_max) * broken_threshold, broken_threshold);
                        top_pct = Math.min((top / scale_max) * broken_threshold, broken_threshold);
                    }} else {{
                        my_pct = (my / max) * 100;
                        total_pct = (total / max) * 100;
                        top_pct = (top / max) * 100;
                    }}
                    
                    // Staggering labels if they overlap
                    let total_transform = "translateX(-50%)";
                    let total_align = "center";
                    let top_transform = "translateX(-50%)";
                    let top_align = "center";
                    
                    let overlap_th = 18;
                    
                    if (Math.abs(my_pct - top_pct) < overlap_th) {{
                        if (my <= top) {{
                            top_transform = "translateX(10px)";
                            top_align = "left";
                        }} else {{
                            top_transform = "translateX(calc(-100% - 10px))";
                            top_align = "right";
                        }}
                    }}
                    
                    if (Math.abs(my_pct - total_pct) < overlap_th) {{
                        if (my <= total) {{
                            total_transform = "translateX(10px)";
                            total_align = "left";
                        }} else {{
                            total_transform = "translateX(calc(-100% - 10px))";
                            total_align = "right";
                        }}
                    }}

                    if (Math.abs(total_pct - top_pct) < overlap_th) {{
                        if (total <= top) {{
                            total_transform = "translateX(calc(-100% - 10px))";
                            total_align = "right";
                            top_transform = "translateX(10px)";
                            top_align = "left";
                        }} else {{
                            top_transform = "translateX(calc(-100% - 10px))";
                            top_align = "right";
                            total_transform = "translateX(10px)";
                            total_align = "left";
                        }}
                    }}
                    
                    let barBg = currentTheme === 'dark' ? '#3A3A3A' : '#EAECEF';
                    let darkBarBg = currentTheme === 'dark' ? '#555' : '#8A8F9B';
                    
                    let barTop = 10;
                    let circleTop = 18;
                    let textTop = 32;
                    let textTotalTop = textTop;
                    let textTopTop = textTop;
                    let total_height = 22;
                    let top_height = 22;
                    
                    let html = `
                    <div id="val-time-inner" style="position: relative; width: calc(100% - 40px); margin: 16px 20px 0 20px; height: 60px; font-family: 'SUIT', sans-serif;">
                        
                        <!-- The Background Bar -->
                        <div class="val-bar" style="position: absolute; left: 0; right: 0; top: ${{barTop}}px; height: 16px; background: ${{barBg}}; z-index: 1;"></div>
                        
                        ${{is_broken ? `
                        <!-- Broken Axis Darker Part -->
                        <div class="val-bar" style="position: absolute; left: ${{broken_threshold}}%; right: 0; top: ${{barTop}}px; height: 16px; background: ${{darkBarBg}}; z-index: 2;"></div>
                        <!-- The Wave -->
                        <div class="val-bar" style="position: absolute; left: ${{broken_threshold}}%; top: ${{barTop}}px; width: 10px; height: 16px; z-index: 3; transform: translateX(-50%);">
                            <svg width="10" height="16" viewBox="0 0 10 16">
                                <path d="M5 0 Q10 2 5 4 T5 8 Q10 10 5 12 T5 16" stroke="${{cardBg}}" stroke-width="3" fill="none"/>
                            </svg>
                        </div>
                        ` : ''}}
                        
                        <!-- The Green Bar (0 to My Pct) -->
                        <div class="val-bar" style="position: absolute; left: 0; width: ${{my_pct}}%; top: ${{barTop}}px; height: 16px; background: #00C73C; z-index: 4;"></div>
                        
                        <!-- The Circle -->
                        <div class="val-circle" style="position: absolute; left: ${{my_pct}}%; top: ${{circleTop}}px; transform: translate(-50%, -50%); width: 14px; height: 14px; border-radius: 50%; background: #FFF; border: 3px solid #00C73C; z-index: 5;"></div>
                        
                        <!-- 0 Text (Only if circle is far enough) -->
                        ${{my_pct > 8 ? `<div class="val-zero-text" style="position: absolute; left: 0; top: ${{textTop}}px; font-size: 11px; color: ${{textCol}}; opacity: 0.6; transform: translateX(-50%);">0</div>` : ''}}
                        
                        <!-- My Value Text under circle -->
                        <div class="val-my-text" style="position: absolute; left: ${{my_pct}}%; top: ${{textTop}}px; font-size: 12px; color: #00C73C; font-weight: bold; transform: translateX(-50%); z-index: 6;">${{my}}</div>
                        
                        <!-- Max Text -->
                        <div class="val-max-text" style="position: absolute; right: 0; top: ${{textTop}}px; font-size: 11px; color: ${{textCol}}; opacity: 0.6; transform: translateX(50%);">${{max.toLocaleString()}}</div>
                        
                        <!-- Service Total Line & Text -->
                        ${{total > 0 ? `
                        <div class="val-bar-line" style="position: absolute; left: ${{total_pct}}%; top: ${{barTop}}px; height: ${{total_height}}px; width: 1px; border-left: 1px dotted ${{textCol}}; opacity: 0.5; z-index: 4;"></div>
                        
                        <div class="val-label label-normal" style="position: absolute; left: ${{total_pct}}%; top: ${{textTotalTop}}px; transform: ${{total_transform}}; text-align: ${{total_align}}; font-size: 10px; color: ${{textCol}}; opacity: 0.7; white-space: nowrap; line-height: 1.2; padding: 0 4px;">
                            <span style="font-size: 12px; font-weight: bold;">${{total}}</span><br>서비스 전체 평균
                        </div>
                        <div class="label-export" style="left: ${{total_pct}}%; transform: ${{total_transform}}; text-align: ${{total_align}}; color: ${{textCol}}; opacity: 0.8;">서비스 전체 평균 ${{total}}</div>
                        ` : ''}}
                        
                        <!-- Top Group Line & Text -->
                        ${{top > 0 ? `
                        <div class="val-bar-line" style="position: absolute; left: ${{top_pct}}%; top: ${{barTop}}px; height: ${{top_height}}px; width: 1px; border-left: 1px dotted #5C80F8; z-index: 4;"></div>
                        
                        <div class="val-label label-normal" style="position: absolute; left: ${{top_pct}}%; top: ${{textTopTop}}px; transform: ${{top_transform}}; text-align: ${{top_align}}; font-size: 10px; color: #5C80F8; white-space: nowrap; line-height: 1.2; padding: 0 4px;">
                            <span style="font-size: 12px; font-weight: bold;">${{top}}</span><br>상위 그룹 평균
                        </div>
                        ` : ''}}
                    </div>
                    `;
                    document.getElementById('val-time-container').innerHTML = html;
                    
                    let total_views = views.length > 0 ? views[views.length - 1] : 0;
                    document.getElementById('val-views').innerText = total_views.toLocaleString();
                    
                    let inflowHtml = '';
                    if (inflow.length === 0) {{
                        inflowHtml = '<tr><td colspan="4" style="text-align:center; opacity:0.6; padding:30px;">데이터가 없습니다.</td></tr>';
                    }} else {{
                        for(let i=0; i<inflow.length; i++) {{
                            let p = inflow[i].percent || 0;
                            let v = inflow[i].value || 0;
                            inflowHtml += `<tr>
                                <td>${{i+1}}</td>
                                <td><span class="ellipsis" title="${{inflow[i].name}}">${{inflow[i].name}}</span></td>
                                <td>${{p.toFixed(1)}}%</td>
                                <td>${{v.toLocaleString()}}</td>
                            </tr>`;
                        }}
                    }}
                    document.getElementById('tbody-inflow').innerHTML = inflowHtml;
                    
                    let rankHtml = '';
                    if (rank_posts.length === 0) {{
                        rankHtml = '<tr><td colspan="3" style="text-align:center; opacity:0.6; padding:30px;">데이터가 없습니다.</td></tr>';
                    }} else {{
                        for(let i=0; i<rank_posts.length; i++) {{
                            rankHtml += `<tr>
                                <td>${{i+1}}</td>
                                <td><span class="ellipsis" title="${{rank_posts[i].title}}">${{rank_posts[i].title}}</span></td>
                                <td>${{rank_posts[i].views.toLocaleString()}}</td>
                            </tr>`;
                        }}
                    }}
                    document.getElementById('tbody-rank').innerHTML = rankHtml;
                }}
                
                function updateTheme(newTheme, newBgColor, newCardBg, newBorderColor, newTextColor) {{
                    document.body.style.backgroundColor = newBgColor;
                    
                    var cards = document.querySelectorAll('.card, .chart-container, .table-box, th');
                    cards.forEach(function(d) {{
                        d.style.backgroundColor = newCardBg;
                        d.style.borderColor = newBorderColor;
                    }});
                    
                    var borders = document.querySelectorAll('th, td');
                    borders.forEach(function(d) {{
                        d.style.borderBottomColor = newBorderColor;
                    }});
                    
                    var texts = document.querySelectorAll('.card-title, .card-value, .table-box h3, th, td');
                    texts.forEach(function(d) {{
                        d.style.color = newTextColor;
                    }});
                    
                    currentTheme = newTheme;
                    textCol = newTextColor;
                    cardBg = newCardBg;
                    borderColor = newBorderColor;
                    
                    mainChart.dispose();
                    mainChart = echarts.init(document.getElementById('main'), currentTheme);
                    
                    mainOption.title.textStyle.color = textCol;
                    mainOption.legend.textStyle.color = textCol;
                    mainOption.xAxis[0].axisLine.lineStyle.color = textCol;
                    mainOption.xAxis[0].axisLabel.color = textCol;
                    mainOption.yAxis[0].splitLine.lineStyle.color = textCol;
                    mainOption.yAxis[0].axisLabel.color = textCol;
                    mainChart.setOption(mainOption);
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
            
        if hasattr(self, 'month_lbl'):
            self.month_lbl.setStyleSheet(f"color: {text_color}; background: transparent;")

    def export_image(self):
        if not hasattr(self, 'chart_view'): return
        company_name = self.company_combo.currentText()
        default_name = f"{company_name}_통계.png"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "통계 이미지 저장",
            os.path.join(os.path.expanduser("~"), "Desktop", default_name),
            "Images (*.png)"
        )
        
        if not file_path:
            return
            
        old_size_policy = self.chart_view.sizePolicy()
        old_min_size = self.chart_view.minimumSize()
        old_max_size = self.chart_view.maximumSize()
        
        is_dark = isDarkTheme()
        theme_str = 'dark' if is_dark else 'light'
        bg_color = '#202020' if is_dark else '#F3F3F3'
        card_bg = '#2C2C2C' if is_dark else '#FFFFFF'
        border_color = '#3A3A3A' if is_dark else '#E5E5E5'
        text_color = '#FFFFFF' if is_dark else '#000000'
        
        js_light = f"document.body.classList.add('export-mode'); updateTheme('light', '#FFFFFF', '#FFFFFF', '#E5E5E5', '#000000'); document.getElementById('inflow-title').innerText = '검색 유입 분석'; document.getElementById('rank-title').innerText = '게시물 조회수 순위'; mainOption.tooltip.show = false; mainOption.xAxis[0].axisLabel.interval = 0; mainOption.xAxis[0].axisLabel.fontSize = 9; mainChart.setOption(mainOption); mainChart.dispatchAction({{type: 'hideTip'}});"
        self.chart_view.page().runJavaScript(js_light)
        
        self.chart_view.setFixedSize(1000, 560)
        self.chart_view.page().runJavaScript("mainChart.resize();")
        
        QTimer.singleShot(600, lambda: self._do_capture(file_path, old_min_size, old_max_size, old_size_policy, theme_str, bg_color, card_bg, border_color, text_color))

    def _do_capture(self, file_path, old_min_size, old_max_size, old_size_policy, theme_str, bg_color, card_bg, border_color, text_color):
        pixmap = self.chart_view.grab()
        pixmap.save(file_path, "PNG")
        
        self.chart_view.setMinimumSize(old_min_size)
        self.chart_view.setMaximumSize(old_max_size)
        self.chart_view.setSizePolicy(old_size_policy)
        
        js_restore = f"document.body.classList.remove('export-mode'); updateTheme('{theme_str}', '{bg_color}', '{card_bg}', '{border_color}', '{text_color}'); document.getElementById('inflow-title').innerText = '검색 유입 분석 TOP 10'; document.getElementById('rank-title').innerText = '게시물 조회수 순위 TOP 10'; mainOption.tooltip.show = true; mainOption.xAxis[0].axisLabel.interval = 'auto'; mainOption.xAxis[0].axisLabel.fontSize = 12; mainChart.setOption(mainOption);"
        self.chart_view.page().runJavaScript(js_restore)
        self.chart_view.page().runJavaScript("mainChart.resize();")
        
        InfoBar.success("저장 완료", f"이미지가 {file_path}에 저장되었습니다.", duration=3000, parent=self)
