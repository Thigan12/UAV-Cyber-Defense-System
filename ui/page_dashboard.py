import os
import time
import collections
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QFrame, QTableWidget, QTableWidgetItem, QPushButton, 
                             QHeaderView, QGridLayout, QSizePolicy)
from PyQt5.QtCore import Qt, QUrl, QTimer, QPropertyAnimation, QVariantAnimation, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen, QFont, QBrush
from PyQt5.QtWebEngineWidgets import QWebEngineView

from ui.page_live_map import MapInterceptPage

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ui.theme import *


class CircularGauge(QWidget):
    """Custom circular gauge for confidence score (T2.5)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(120, 120)
        self.value = 0.0
        self.color = SAFE_GREEN
        
    def set_value(self, val, color):
        self.value = val
        self.color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        margin = 10
        width = rect.width() - 2 * margin
        height = rect.height() - 2 * margin
        size = min(width, height)
        x = rect.width() // 2 - size // 2
        y = rect.height() // 2 - size // 2

        # Draw background track
        pen_bg = QPen(QColor(BORDER_DEFAULT), 8, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(x, y, size, size, 0, 360 * 16)
        
        # Draw foreground progress
        pen_fg = QPen(QColor(self.color), 8, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen_fg)
        span_angle = int(-self.value * 360 * 16) # Negative for clockwise
        painter.drawArc(x, y, size, size, 90 * 16, span_angle)
        
        # Draw text
        painter.setPen(QColor(self.color))
        font = QFont("Arial", 16, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{self.value * 100:.1f}%")


class DashboardPage(QWidget):
    """Main dashboard — threat banner, map, graphs, AI panel, attack logs, control panel."""
    fly_command_requested = pyqtSignal(float, float)
    btn_command_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.home_lat = 0
        self.home_lon = 0
        self.current_lat = 0
        self.current_lon = 0
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)
        
        self.build_telemetry_bar()
        self.build_threat_banner()
        
        # Main Middle Layout
        self.middle_layout = QHBoxLayout()
        self.main_layout.addLayout(self.middle_layout, stretch=5)
        
        # Map goes on the left
        self.build_map_panel()
        
        # Right side split: Graphs and AI Panel
        self.right_middle_layout = QHBoxLayout()
        self.middle_layout.addLayout(self.right_middle_layout, stretch=3)
        
        self.build_graphs_panel()
        
        # Far right: AI Panel + Mitigation Checklist
        self.far_right_layout = QVBoxLayout()
        self.right_middle_layout.addLayout(self.far_right_layout, stretch=1)
        
        self.build_ai_panel()
        self.build_mitigation_checklist()
        
        # Bottom Layout
        self.bottom_layout = QHBoxLayout()
        self.main_layout.addLayout(self.bottom_layout, stretch=2)
        
        self.build_attack_log_table()
        self.build_control_panel()
        
        # Connect to MainWindow adapter signals when page is mounted
        # (This will be done from MainWindow, but we can setup the slots here)
        self.current_attack_class = 0
        self.consensus_count = 0

    def build_telemetry_bar(self):
        """T2.1 — UAV Telemetry Live Bar"""
        self.tel_bar = QFrame()
        self.tel_bar.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        bar_layout = QHBoxLayout(self.tel_bar)
        
        self.tel_metrics = {}
        metrics = ["Altitude", "Ground Speed", "Vertical Speed", "Heading", 
                   "Latitude", "Longitude", "Satellites", "Battery"]
        
        for m in metrics:
            card = QVBoxLayout()
            lbl_title = QLabel(m.upper())
            lbl_title.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; font-weight: bold;")
            lbl_val = QLabel("--")
            lbl_val.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
            card.addWidget(lbl_title)
            card.addWidget(lbl_val)
            self.tel_metrics[m] = lbl_val
            bar_layout.addLayout(card)
            
        self.main_layout.addWidget(self.tel_bar)

    def build_threat_banner(self):
        """T2.2 — Threat Detected Alert Banner"""
        self.banner = QFrame()
        self.banner.setFixedHeight(80)
        self.banner.setStyleSheet(f"background-color: #2a0000; border: 2px solid {ALERT_RED}; border-radius: 5px;")
        self.banner.hide() # Hidden by default
        
        banner_layout = QHBoxLayout(self.banner)
        
        # Left: Alert Text
        self.lbl_alert_title = QLabel("⚠ THREAT DETECTED")
        self.lbl_alert_title.setStyleSheet(f"color: {ALERT_RED}; font-size: 24px; font-weight: bold;")
        self.lbl_alert_sub = QLabel("COMMUNICATION SEVERED\\nAUTO RTL ACTIVATED")
        self.lbl_alert_sub.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
        
        left_vbox = QVBoxLayout()
        left_vbox.addWidget(self.lbl_alert_title)
        left_vbox.addWidget(self.lbl_alert_sub)
        banner_layout.addLayout(left_vbox)
        
        banner_layout.addStretch()
        
        # Center: Attack Details
        center_vbox = QVBoxLayout()
        self.lbl_attack_name = QLabel("DETECTED ATTACK: --")
        self.lbl_attack_name.setStyleSheet(f"color: {ALERT_RED}; font-size: 14px; font-weight: bold;")
        self.lbl_consensus = QLabel("CONSENSUS: 0 / 3")
        self.lbl_consensus.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        center_vbox.addWidget(self.lbl_attack_name)
        center_vbox.addWidget(self.lbl_consensus)
        banner_layout.addLayout(center_vbox)
        
        banner_layout.addStretch()
        
        # Right: Risk Level
        right_vbox = QVBoxLayout()
        self.lbl_risk = QLabel("RISK LEVEL: CRITICAL")
        self.lbl_risk.setStyleSheet(f"color: {ALERT_RED}; font-size: 16px; font-weight: bold;")
        self.lbl_conf_banner = QLabel("CONFIDENCE: --")
        self.lbl_conf_banner.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px;")
        right_vbox.addWidget(self.lbl_risk)
        right_vbox.addWidget(self.lbl_conf_banner)
        banner_layout.addLayout(right_vbox)
        
        self.main_layout.addWidget(self.banner)

    def build_map_panel(self):
        """T2.3 — Live Map Panel (Left)"""
        self.map_frame = QFrame()
        self.map_frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        map_layout = QVBoxLayout(self.map_frame)
        map_layout.setContentsMargins(0, 0, 0, 0)
        
        # QWebEngineView for Leaflet Map
        self.map_view = QWebEngineView()
        
        # Intercept JS console logs for right-clicks
        self.intercept_page = MapInterceptPage(self.map_view, self.handle_map_command)
        self.map_view.setPage(self.intercept_page)
        
        # Load local HTML file
        map_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'map.html'))
        self.map_view.setUrl(QUrl.fromLocalFile(map_path))
        
        map_layout.addWidget(self.map_view)
        self.middle_layout.addWidget(self.map_frame, stretch=4)

    def build_graphs_panel(self):
        """T2.4 — Live Telemetry Graphs Panel (Right)"""
        self.graph_frame = QFrame()
        self.graph_frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        graph_layout = QVBoxLayout(self.graph_frame)
        
        lbl = QLabel("LIVE TELEMETRY GRAPHS")
        lbl.setStyleSheet(f"color: {ACCENT_CYAN}; font-weight: bold;")
        graph_layout.addWidget(lbl)
        
        # Matplotlib Figure
        self.fig = Figure(figsize=(5, 6), facecolor=PANEL_BG)
        self.canvas = FigureCanvas(self.fig)
        
        # Setup 5 axes
        self.axs = []
        titles = ["Altitude (m)", "Ground Speed (m/s)", "GPS Jump Magnitude (m)", 
                  "RC Channel 1 Raw", "Servo Output 1 (PWM)"]
        colors = [WARN_YELLOW, ACCENT_CYAN, ALERT_RED, WARN_ORANGE, ACCENT_PURPLE]
        
        for i in range(5):
            ax = self.fig.add_subplot(5, 1, i+1)
            ax.set_facecolor(BG_DARK)
            ax.tick_params(colors=TEXT_MUTED, labelsize=8)
            ax.spines['bottom'].set_color(BORDER_DEFAULT)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color(BORDER_DEFAULT)
            ax.set_title(titles[i], color=TEXT_PRIMARY, fontsize=9, loc='left', pad=2)
            self.axs.append({"ax": ax, "color": colors[i], "line": None})
            
        self.fig.tight_layout(pad=1.0)
        graph_layout.addWidget(self.canvas)
        
        self.right_middle_layout.addWidget(self.graph_frame, stretch=3)
        
        # Data deques for last 60 ticks
        self.time_data = collections.deque(maxlen=60)
        self.graph_data = [collections.deque(maxlen=60) for _ in range(5)]
        self._graph_tick = 0
        
    def build_ai_panel(self):
        """T2.5 — AI Prediction Panel"""
        self.ai_frame = QFrame()
        self.ai_frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        ai_layout = QVBoxLayout(self.ai_frame)
        
        lbl = QLabel("AI PREDICTION (LIVE)")
        lbl.setStyleSheet(f"color: {ACCENT_PURPLE}; font-weight: bold;")
        ai_layout.addWidget(lbl)
        
        self.lbl_current_pred = QLabel("NORMAL FLIGHT")
        self.lbl_current_pred.setStyleSheet(f"color: {SAFE_GREEN}; font-size: 20px; font-weight: bold;")
        self.lbl_current_pred.setAlignment(Qt.AlignCenter)
        ai_layout.addWidget(self.lbl_current_pred)
        
        self.gauge = CircularGauge()
        ai_layout.addWidget(self.gauge, alignment=Qt.AlignCenter)
        
        lbl_hist = QLabel("Prediction History (Last 20s)")
        lbl_hist.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
        ai_layout.addWidget(lbl_hist)
        
        # History dots placeholder
        self.history_layout = QHBoxLayout()
        self.history_layout.setSpacing(2)
        for _ in range(20):
            dot = QLabel()
            dot.setFixedSize(8, 15)
            dot.setStyleSheet(f"background-color: {SAFE_GREEN}; border-radius: 2px;")
            self.history_layout.addWidget(dot)
        ai_layout.addLayout(self.history_layout)
        
        self.far_right_layout.addWidget(self.ai_frame)

    def build_mitigation_checklist(self):
        """T2.6 — Zero-Trust Mitigation Status"""
        self.checklist_frame = QFrame()
        self.checklist_frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        cl_layout = QVBoxLayout(self.checklist_frame)
        
        lbl = QLabel("ZERO-TRUST MITIGATION STATUS")
        lbl.setStyleSheet(f"color: {ACCENT_CYAN}; font-weight: bold; font-size: 11px;")
        cl_layout.addWidget(lbl)
        
        self.checklist_steps = []
        steps = ["Anomaly Detected (AI)", "Consensus Reached (3/3)", 
                 "Communication Severed", "RTL Command Sent", 
                 "Returning To Launch (RTL)", "Safe Landing"]
                 
        for step in steps:
            row = QHBoxLayout()
            icon = QLabel("✔")
            icon.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: bold;")
            lbl_step = QLabel(step)
            lbl_step.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px;")
            status = QLabel("PENDING")
            status.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; font-weight: bold;")
            
            row.addWidget(icon)
            row.addWidget(lbl_step)
            row.addStretch()
            row.addWidget(status)
            
            self.checklist_steps.append((icon, lbl_step, status))
            cl_layout.addLayout(row)
            
        self.far_right_layout.addWidget(self.checklist_frame)

    def build_attack_log_table(self):
        """T2.7 — Attack Logs Table"""
        self.log_frame = QFrame()
        self.log_frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        log_layout = QVBoxLayout(self.log_frame)
        
        lbl = QLabel("ATTACK LOGS")
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold;")
        log_layout.addWidget(lbl)
        
        self.log_table = QTableWidget(0, 6)
        self.log_table.setHorizontalHeaderLabels(["TIME (UTC)", "ATTACK TYPE", "CONFIDENCE", "LOCATION (Lat, Lon)", "ACTION TAKEN", "STATUS"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.log_table.setStyleSheet(f"""
            QTableWidget {{ background-color: transparent; color: {TEXT_PRIMARY}; border: none; gridline-color: {BORDER_DEFAULT}; }}
            QHeaderView::section {{ background-color: {CARD_BG}; color: {TEXT_MUTED}; font-weight: bold; border: none; padding: 5px; }}
        """)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        log_layout.addWidget(self.log_table)
        self.bottom_layout.addWidget(self.log_frame, stretch=3)

    def build_control_panel(self):
        """T2.8 — Control Panel"""
        self.ctrl_frame = QFrame()
        self.ctrl_frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        ctrl_layout = QVBoxLayout(self.ctrl_frame)
        
        lbl = QLabel("CONTROL PANEL")
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold;")
        ctrl_layout.addWidget(lbl)
        
        grid = QGridLayout()
        grid.setSpacing(10)
        
        # Buttons
        self.btn_start = QPushButton("▶ Start Monitoring")
        self.btn_start.setStyleSheet(f"background-color: #004d00; color: white; border-radius: 3px; padding: 8px;")
        self.btn_start.clicked.connect(lambda: self.btn_command_requested.emit("start"))
        
        self.btn_stop = QPushButton("⏹ Stop Monitoring")
        self.btn_stop.setStyleSheet(f"background-color: #333; color: white; border-radius: 3px; padding: 8px;")
        self.btn_stop.clicked.connect(lambda: self.btn_command_requested.emit("stop"))
        
        self.btn_rtl = QPushButton("↩ Manual RTL")
        self.btn_rtl.setStyleSheet(f"background-color: #003366; color: white; border-radius: 3px; padding: 8px;")
        self.btn_rtl.clicked.connect(lambda: self.btn_command_requested.emit("rtl"))
        
        self.btn_export = QPushButton("📄 Export Report")
        self.btn_export.setStyleSheet(f"background-color: #331a00; color: white; border-radius: 3px; padding: 8px;")
        self.btn_export.clicked.connect(lambda: self.btn_command_requested.emit("export"))
        
        self.btn_clear = QPushButton("🗑 Clear Logs")
        self.btn_clear.setStyleSheet(f"background-color: #333; color: white; border-radius: 3px; padding: 8px;")
        self.btn_clear.clicked.connect(lambda: self.btn_command_requested.emit("clear"))
        
        self.btn_settings = QPushButton("⚙ Settings")
        self.btn_settings.setStyleSheet(f"background-color: #333; color: white; border-radius: 3px; padding: 8px;")
        self.btn_settings.clicked.connect(lambda: self.btn_command_requested.emit("settings"))
        
        grid.addWidget(self.btn_start, 0, 0)
        grid.addWidget(self.btn_stop, 0, 1)
        grid.addWidget(self.btn_rtl, 0, 2)
        grid.addWidget(self.btn_export, 1, 0)
        grid.addWidget(self.btn_clear, 1, 1)
        grid.addWidget(self.btn_settings, 1, 2)
        
        ctrl_layout.addLayout(grid)
        
        self.lbl_sys_status = QLabel("System Status: ● All Systems Operational")
        self.lbl_sys_status.setStyleSheet(f"color: {SAFE_GREEN}; margin-top: 10px;")
        ctrl_layout.addWidget(self.lbl_sys_status)
        
        self.bottom_layout.addWidget(self.ctrl_frame, stretch=2)

    def handle_map_command(self, msg: str):
        """Parse FLY_TO command from Leaflet and emit signal to backend"""
        try:
            coords = msg.replace("FLY_TO:", "").split(",")
            self.fly_command_requested.emit(float(coords[0]), float(coords[1]))
        except Exception as e:
            print(f"Dashboard Map command parse error: {e}")

    def update_map(self, data: dict):
        """Heavy update — called at 2Hz. Updates drone position on dashboard map."""
        if 'lat' in data and 'lon' in data:
            self.current_lat = data['lat']
            self.current_lon = data['lon']
            alt = data.get('alt', 0)
            spd = data.get('spd', 0)
            
            if self.home_lat == 0 and self.current_lat != 0:
                self.home_lat = self.current_lat
                self.home_lon = self.current_lon
                self.map_view.page().runJavaScript(f"setHomePosition({self.home_lat}, {self.home_lon})")
            
            self.map_view.page().runJavaScript(f"updateDronePosition({self.current_lat}, {self.current_lon}, {alt}, {spd})")
            self.map_view.page().runJavaScript(f"addPathPoint({self.current_lat}, {self.current_lon})")
            
            is_attack = data.get('is_attack', False)
            if is_attack:
                self.map_view.page().runJavaScript(f"showAttackZone({self.current_lat}, {self.current_lon})")
            else:
                self.map_view.page().runJavaScript("clearAttackZone()")

    # Slot updates to be wired via MainWindow
    def update_telemetry_bar(self, data: dict):
        """Light update — runs at full 10Hz. Text labels only, no canvas redraw."""
        if 'alt' in data: self.tel_metrics["Altitude"].setText(f"{data['alt']:.1f} m")
        if 'spd' in data: self.tel_metrics["Ground Speed"].setText(f"{data['spd']:.1f} m/s")
        if 'vz' in data: self.tel_metrics["Vertical Speed"].setText(f"{data['vz']:.1f} m/s")
        if 'heading' in data: self.tel_metrics["Heading"].setText(f"{data['heading']}°")
        if 'lat' in data: self.tel_metrics["Latitude"].setText(f"{data['lat']:.6f}°")
        if 'lon' in data: self.tel_metrics["Longitude"].setText(f"{data['lon']:.6f}°")
        if 'satellites' in data: self.tel_metrics["Satellites"].setText(str(data['satellites']))
        if 'battery' in data: self.tel_metrics["Battery"].setText(f"{data['battery']}%")

        # Update consensus banner label in real-time
        if 'consensus' in data:
            self.lbl_consensus.setText(f"CONSENSUS: {int(data['consensus'])} / 3")

        # Zero-Trust Checklist State Machine
        is_attack = data.get('is_attack', False)
        consensus = data.get('consensus', 0)
        flight_mode = data.get('flight_mode', 0)
        armed = data.get('armed', 0)
        alt = data.get('alt', 0.0)
        is_compromised = data.get('is_compromised', False)

        step_idx = -1
        if is_attack:
            step_idx = 0  # Anomaly Detected (AI)
            if consensus >= 3:
                step_idx = 1  # Consensus Reached (3/3)
                if is_compromised:
                    step_idx = 2  # Communication Severed
                    if flight_mode in [4, 6, 9]:
                        step_idx = 3  # RTL Command Sent
                        if flight_mode in [6, 9]:
                            step_idx = 4  # Returning To Launch (RTL)
                            if alt < 1.0 and armed == 0:
                                step_idx = 6  # Safe Landing (All steps completed)
        
        self.update_mitigation_checklist(step_idx)

        # Update dashboard attack logs table
        self.update_attack_logs(data)

        # Accumulate graph data at 10Hz — but don't redraw yet
        if 'alt' in data:
            self.time_data.append(self._graph_tick)
            self._graph_tick += 1
            
            self.graph_data[0].append(data['alt'])
            self.graph_data[1].append(data.get('spd', 0))
            self.graph_data[2].append(data.get('gps_jump', 0.0))
            self.graph_data[3].append(data.get('chan1_raw', 1500))
            self.graph_data[4].append(data.get('servo1_raw', 1500))

    def update_graphs(self, data: dict):
        """Heavy update — called at 2Hz only. Redraws Matplotlib canvas."""
        x_data = list(self.time_data)
        for i, deque_data in enumerate(self.graph_data):
            y_data = list(deque_data)
            min_len = min(len(x_data), len(y_data))
            if min_len > 0:
                x_slice = x_data[:min_len]
                y_slice = y_data[:min_len]
                if self.axs[i]["line"] is None:
                    self.axs[i]["line"], = self.axs[i]["ax"].plot(
                        x_slice, y_slice, color=self.axs[i]["color"])
                else:
                    self.axs[i]["line"].set_data(x_slice, y_slice)
                self.axs[i]["ax"].set_xlim(max(0, x_slice[-1] - 60), max(60, x_slice[-1]))
                self.axs[i]["ax"].set_ylim(min(y_slice) * 0.9, max(y_slice) * 1.1 + 0.1)
        self.canvas.draw_idle()
            
    def update_threat_banner(self, attack_class: int, confidence: float):
        self.current_attack_class = attack_class
        
        if attack_class == 0:
            self.banner.hide()
            self.lbl_current_pred.setText("NORMAL FLIGHT")
            self.lbl_current_pred.setStyleSheet(f"color: {SAFE_GREEN}; font-size: 20px; font-weight: bold;")
            self.gauge.set_value(confidence, SAFE_GREEN)
            self.lbl_sys_status.setText("System Status: ● All Systems Operational")
            self.lbl_sys_status.setStyleSheet(f"color: {SAFE_GREEN}; margin-top: 10px;")
        else:
            self.banner.show()
            name = CLASS_NAMES.get(attack_class, "UNKNOWN")
            self.lbl_current_pred.setText(name.upper())
            self.lbl_current_pred.setStyleSheet(f"color: {ALERT_RED}; font-size: 20px; font-weight: bold;")
            self.lbl_attack_name.setText(f"DETECTED ATTACK: {name.upper()}")
            
            # Beep alarm sound at 1Hz max in the main thread
            now = time.monotonic()
            if now - getattr(self, '_last_beep_time', 0) >= 1.0:
                self._last_beep_time = now
                QApplication.beep()
            
            self.gauge.set_value(confidence, ALERT_RED)
            self.lbl_conf_banner.setText(f"CONFIDENCE: {confidence*100:.1f}%")
            
            self.lbl_sys_status.setText("System Status: ⚠ THREAT ACTIVE")
            self.lbl_sys_status.setStyleSheet(f"color: {ALERT_RED}; margin-top: 10px;")
            
            if confidence >= 0.90:
                self.lbl_risk.setText("RISK LEVEL: CRITICAL")
                self.lbl_risk.setStyleSheet(f"color: {ALERT_RED}; font-size: 16px; font-weight: bold;")
            elif confidence >= 0.70:
                self.lbl_risk.setText("RISK LEVEL: MEDIUM")
                self.lbl_risk.setStyleSheet(f"color: {WARN_ORANGE}; font-size: 16px; font-weight: bold;")
            else:
                self.lbl_risk.setText("RISK LEVEL: LOW")
                self.lbl_risk.setStyleSheet(f"color: {WARN_YELLOW}; font-size: 16px; font-weight: bold;")
                
    def update_mitigation_checklist(self, step: int):
        for i, (icon, lbl, status) in enumerate(self.checklist_steps):
            if i < step:
                icon.setStyleSheet(f"color: {SAFE_GREEN}; font-weight: bold;")
                status.setText("DONE")
                status.setStyleSheet(f"color: {SAFE_GREEN}; font-size: 10px; font-weight: bold;")
            elif i == step:
                icon.setStyleSheet(f"color: {ACCENT_CYAN}; font-weight: bold;")
                status.setText("IN PROGRESS")
                status.setStyleSheet(f"color: {ACCENT_CYAN}; font-size: 10px; font-weight: bold;")
            else:
                icon.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: bold;")
                status.setText("PENDING")
                status.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; font-weight: bold;")

    def update_attack_logs(self, data: dict):
        """Update dashboard attack log table when an attack occurs."""
        import time, datetime
        # Initialize throttle state on first call
        if not hasattr(self, 'last_logged_class'):
            self.last_logged_class = -1
            self.last_log_time = 0.0

        attack_class = data.get('attack_type', 0)
        if attack_class == 0:
            # Reset so next attack is always logged
            self.last_logged_class = 0
            return

        current_time = time.time()
        # Throttle: Only log if it's a new attack class or 10 s since last entry
        if attack_class == self.last_logged_class and (current_time - self.last_log_time) < 10:
            return

        self.last_logged_class = attack_class
        self.last_log_time = current_time

        name = CLASS_NAMES.get(attack_class, "Unknown")
        conf = data.get('confidence', 0.0)
        lat  = data.get('lat', 0.0)
        lon  = data.get('lon', 0.0)

        row = self.log_table.rowCount()
        self.log_table.insertRow(row)

        bg_colors = {
            1: QColor("#3d0000"),  # RC Hijack
            2: QColor("#3d1a00"),  # Mode Forcing
            3: QColor("#2d2d00"),  # GPS Spoofing
            4: QColor("#3d003d"),  # Disarm
        }
        bg_brush = QBrush(bg_colors.get(attack_class, QColor(PANEL_BG)))

        time_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        action_map = {
            1: "RC Overrides Disabled",
            2: "Mode Locked to STABILIZE",
            3: "Emergency LAND Mode Forced",
            4: "RTL Altitude Restored & RTL Initiated"
        }
        action_taken = action_map.get(attack_class, "RTL Activated")

        items = [
            QTableWidgetItem(time_str),
            QTableWidgetItem(name),
            QTableWidgetItem(f"{conf*100:.1f}%"),
            QTableWidgetItem(f"{lat:.4f}, {lon:.4f}"),
            QTableWidgetItem(action_taken),
            QTableWidgetItem("Mitigated")
        ]

        items[1].setForeground(QBrush(QColor(CLASS_COLOURS.get(attack_class, SAFE_GREEN))))
        items[5].setForeground(QBrush(QColor(ALERT_RED)))

        for i, item in enumerate(items):
            item.setBackground(bg_brush)
            self.log_table.setItem(row, i, item)

