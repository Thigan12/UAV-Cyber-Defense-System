import sys
import time
import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QStackedWidget,
                             QFrame, QSizePolicy)
from PyQt5.QtCore import QTimer, pyqtSignal, QObject, Qt
from PyQt5.QtGui import QFont

# Import themes and pages
from ui.theme import *
from ui.page_dashboard import DashboardPage
from ui.page_telemetry import TelemetryPage
from ui.page_ai_detection import AIDetectionPage
from ui.page_live_map import LiveMapPage
from ui.page_threat_logs import ThreatLogsPage
from ui.page_reports import ReportsPage
from ui.page_settings import SettingsPage

# Import the original UAVDataBridge backend (Task 9 will upgrade it later)
from desktop_app import UAVDataBridge

class BridgeSignalAdapter(QObject):
    """Wraps UAVDataBridge callbacks into PyQt signals."""
    telemetry_updated = pyqtSignal(dict)       # Fires every packet (10Hz) — light updates
    telemetry_heavy = pyqtSignal(dict)         # Throttled to 2Hz — graphs, map, AI page
    attack_detected = pyqtSignal(int, float)
    log_message = pyqtSignal(str, str)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UAV Cyber-Physical IDS Dashboard")
        self.setMinimumSize(1400, 900)
        self.setStyleSheet(f"background-color: {BG_DARK}; color: {TEXT_PRIMARY};")

        # Initialize backend adapter
        self.bridge_adapter = BridgeSignalAdapter()
        self._last_heavy_update = 0.0  # Throttle timestamp for graph/map updates
        
        # Initialize UAVDataBridge (passing our adapter's callback method)
        self.bridge = UAVDataBridge(self.bridge_callback)

        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Build UI Components
        self.build_header_bar()
        
        # Content Layout (Sidebar + Pages)
        self.content_layout = QHBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.main_layout.addLayout(self.content_layout)

        self.build_sidebar()
        self.build_page_switcher()
        
        # Start Header Updates
        self.header_timer = QTimer()
        self.header_timer.timeout.connect(self.update_header_data)
        self.header_timer.start(1000) # 1Hz updates

    def build_header_bar(self):
        self.header = QFrame()
        self.header.setFixedHeight(70)
        self.header.setStyleSheet(f"background-color: {HEADER_BG}; border-bottom: 2px solid {BORDER_DEFAULT};")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        # Left: Logo and Title
        title_lbl = QLabel("UAV CYBER-PHYSICAL IDS\nZero-Trust Intrusion Detection System\nMSC CYBERSECURITY PROJECT\nR.THIGAMPARAN")
        title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        header_layout.addWidget(title_lbl)
        
        header_layout.addStretch()

        # Centre: Status Pills
        self.status_pills = {}
        pill_names = ["CONNECTION", "UAV STATUS", "ARMED", "GPS", "BATTERY", "TIME (UTC)"]
        
        for name in pill_names:
            pill = QFrame()
            pill.setStyleSheet(f"background-color: transparent; border: none;")
            pill_layout = QVBoxLayout(pill)
            pill_layout.setContentsMargins(10, 5, 10, 5)
            pill_layout.setSpacing(2)
            
            lbl_title = QLabel(name)
            lbl_title.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; font-weight: bold; border: none;")
            lbl_title.setAlignment(Qt.AlignCenter)
            
            lbl_value = QLabel("--")
            lbl_value.setStyleSheet(f"color: {SAFE_GREEN}; font-size: 14px; font-weight: bold; border: none;")
            lbl_value.setAlignment(Qt.AlignCenter)
            
            pill_layout.addWidget(lbl_title)
            pill_layout.addWidget(lbl_value)
            
            self.status_pills[name] = lbl_value
            header_layout.addWidget(pill)

        header_layout.addStretch()

        # Right: Emergency Stop
        self.btn_estop = QPushButton("⚠ EMERGENCY STOP")
        self.btn_estop.setFixedSize(160, 40)
        self.btn_estop.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px solid {ALERT_RED};
                color: {ALERT_RED};
                font-weight: bold;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {ALERT_RED};
                color: #ffffff;
            }}
        """)
        self.btn_estop.clicked.connect(lambda: self.bridge.send_command('LAND'))
        header_layout.addWidget(self.btn_estop)

        self.main_layout.addWidget(self.header)

    def build_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet(f"background-color: {SIDEBAR_BG}; border-right: 1px solid {BORDER_DEFAULT}; border-top: none; border-bottom: none; border-left: none;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(5)

        self.nav_buttons = {}
        pages = [
            ("Dashboard", "page_dashboard"),
            ("Live Telemetry", "page_telemetry"),
            ("Threat Logs", "page_threat_logs"),
            ("AI Detection", "page_ai_detection"),
            ("Map & Path", "page_live_map"),
            ("Reports", "page_reports"),
            ("Settings", "page_settings")
        ]

        for title, obj_name in pages:
            btn = QPushButton(title)
            btn.setFixedHeight(45)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {TEXT_MUTED};
                    border: none;
                    text-align: left;
                    padding-left: 20px;
                    font-size: 14px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {CARD_BG};
                    color: {TEXT_PRIMARY};
                }}
                QPushButton:checked {{
                    background-color: {CARD_BG};
                    color: {ACCENT_CYAN};
                    border-left: 4px solid {ACCENT_CYAN};
                }}
            """)
            btn.setCheckable(True)
            if obj_name:
                btn.clicked.connect(lambda checked, name=obj_name, b=btn: self.switch_page(name, b))
            else:
                btn.setDisabled(True) # Disable unimplemented pages
            
            self.nav_buttons[obj_name] = btn
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # SITL Connection Indicator
        self.sitl_lbl = QLabel("SITL Connection\nudp:127.0.0.1:14550")
        self.sitl_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; padding: 10px; border: none;")
        self.sitl_lbl.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(self.sitl_lbl)

        self.content_layout.addWidget(self.sidebar)

    def build_page_switcher(self):
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet(f"background-color: {BG_DARK}; border: none;")
        
        self.pages = {
            "page_dashboard": DashboardPage(),
            "page_telemetry": TelemetryPage(),
            "page_ai_detection": AIDetectionPage(),
            "page_live_map": LiveMapPage(),
            "page_threat_logs": ThreatLogsPage(),
            "page_settings": SettingsPage(),
            "page_reports": ReportsPage()
        }

        # Wire Signals — Light updates at full 10Hz
        self.bridge_adapter.telemetry_updated.connect(self.pages["page_dashboard"].update_telemetry_bar)
        self.bridge_adapter.attack_detected.connect(self.pages["page_dashboard"].update_threat_banner)
        self.bridge_adapter.telemetry_updated.connect(self.pages["page_threat_logs"].log_attack)

        # Wire Signals — Heavy updates throttled to 2Hz (graphs, map, AI page)
        self.bridge_adapter.telemetry_heavy.connect(self.pages["page_telemetry"].update_metrics)
        self.bridge_adapter.telemetry_heavy.connect(self.pages["page_live_map"].update_map)
        self.bridge_adapter.telemetry_heavy.connect(self.pages["page_dashboard"].update_map)
        self.bridge_adapter.telemetry_heavy.connect(self.pages["page_dashboard"].update_graphs)
        self.bridge_adapter.telemetry_heavy.connect(self.pages["page_ai_detection"].update_prediction_from_data)

        # Wire User Control Commands (Map clicks & Buttons)
        self.pages["page_live_map"].fly_command_requested.connect(self.bridge.fly_to_waypoint)
        self.pages["page_dashboard"].fly_command_requested.connect(self.bridge.fly_to_waypoint)
        self.pages["page_dashboard"].btn_command_requested.connect(self.handle_dashboard_command)
        
        # Wire System Logs to Terminal
        self.bridge_adapter.log_message.connect(self.handle_log_message)

        for name, page in self.pages.items():
            self.stacked_widget.addWidget(page)

        self.content_layout.addWidget(self.stacked_widget)
        
        # Default to dashboard
        self.switch_page("page_dashboard", self.nav_buttons["page_dashboard"])

    def switch_page(self, page_name, active_btn):
        # Update button states
        for btn in self.nav_buttons.values():
            btn.setChecked(False)
        active_btn.setChecked(True)
        
        # Switch page
        if page_name in self.pages:
            self.stacked_widget.setCurrentWidget(self.pages[page_name])

    def handle_dashboard_command(self, cmd: str):
        """Handle button clicks from the dashboard control panel."""
        print(f"[UI COMMAND] {cmd.upper()} requested.")
        try:
            if cmd == "start":
                # Visual feedback — show monitoring is active
                self.pages["page_dashboard"].btn_start.setStyleSheet(
                    "background-color: #007700; color: white; border-radius: 3px; padding: 8px; border: 2px solid #00ff88;")
                self.pages["page_dashboard"].btn_stop.setStyleSheet(
                    "background-color: #333; color: white; border-radius: 3px; padding: 8px;")
                self.bridge_adapter.log_message.emit("[OPERATOR] Monitoring active — AI detection running.", "system")
            elif cmd == "stop":
                # Visual feedback — show monitoring is paused
                self.pages["page_dashboard"].btn_start.setStyleSheet(
                    "background-color: #004d00; color: white; border-radius: 3px; padding: 8px;")
                self.pages["page_dashboard"].btn_stop.setStyleSheet(
                    "background-color: #770000; color: white; border-radius: 3px; padding: 8px; border: 2px solid #ff003c;")
                self.bridge_adapter.log_message.emit("[OPERATOR] Monitoring display paused. Backend still running.", "system")
            elif cmd == "rtl":
                if not self.bridge.is_connected:
                    self.bridge_adapter.log_message.emit("[ERROR] Cannot RTL: UAV not connected.", "alert")
                else:
                    self.bridge.send_command("RTL")
            elif cmd == "clear":
                # Threat logs page uses .table, dashboard page uses .log_table
                self.pages["page_threat_logs"].table.setRowCount(0)
                if hasattr(self.pages["page_threat_logs"], 'attack_log'):
                    self.pages["page_threat_logs"].attack_log.clear()
                self.pages["page_dashboard"].log_table.setRowCount(0)
                if hasattr(self.bridge, 'attack_log'):
                    self.bridge.attack_log.clear()
                # Restore operator control and clear lockouts
                self.bridge.reset_alert()
                # Reset button styles
                self.pages["page_dashboard"].btn_start.setStyleSheet(
                    "background-color: #004d00; color: white; border-radius: 3px; padding: 8px;")
                self.pages["page_dashboard"].btn_stop.setStyleSheet(
                    "background-color: #333; color: white; border-radius: 3px; padding: 8px;")
                self.bridge_adapter.log_message.emit("[OPERATOR] Logs cleared. System reset to normal.", "system")
            elif cmd == "settings":
                self.switch_page("page_settings", self.nav_buttons["page_settings"])
            elif cmd == "export":
                self.pages["page_reports"].set_data(
                    attack_log=getattr(self.bridge, 'attack_log', []),
                    system_info={
                        "battery": getattr(self.bridge, 'battery_pct', "N/A"),
                        "satellites": getattr(self.bridge, 'gps_satellites', "N/A"),
                        "flight_mode": self.bridge.current_flight_mode if hasattr(self.bridge, 'current_flight_mode') else 0,
                    }
                )
                self.switch_page("page_reports", self.nav_buttons["page_reports"])
        except Exception as e:
            print(f"[ERROR] handle_dashboard_command '{cmd}' failed: {e}")
            import traceback
            traceback.print_exc()

    def handle_log_message(self, msg: str, log_type: str):
        """Print bridge log messages to the terminal."""
        if log_type == "alert":
            print(f"\033[91m{msg}\033[0m") # Red text
        elif log_type == "system":
            print(f"\033[96m{msg}\033[0m") # Cyan text
        else:
            print(msg)

    def bridge_callback(self, telemetry=None, msg_log=None, log_type=None):
        """Called by UAVDataBridge thread. Emit PyQt signals safely.
        Light signal: every packet (10Hz). Heavy signal: throttled to 2Hz.
        """
        try:
            if telemetry:
                if isinstance(telemetry, dict):
                    telemetry_data = telemetry
                else:
                    lat, lon, alt, spd, is_attack, confidence, attack_type = telemetry
                    telemetry_data = {
                        'lat': lat, 'lon': lon, 'alt': alt, 'spd': spd,
                        'is_attack': is_attack, 'confidence': confidence,
                        'attack_type': attack_type,
                    }
                
                # Always emit light signal (cheap: text labels only)
                self.bridge_adapter.telemetry_updated.emit(telemetry_data)
                
                # Only emit heavy signal (graphs, map) at max 2Hz
                now = time.monotonic()
                if now - self._last_heavy_update >= 0.5:  # 500ms = 2Hz
                    self._last_heavy_update = now
                    self.bridge_adapter.telemetry_heavy.emit(telemetry_data)
                
                is_attack = telemetry_data.get('is_attack', False)
                is_compromised = telemetry_data.get('is_compromised', False)
                
                if is_compromised:
                    # Lock the banner into RED state showing the threat
                    # Since the drone might be falling or landing, the raw AI is_attack might be false now,
                    # so we force the banner to stay active using the last logged attack type
                    last_attack = 4 # Default to 4 (Disarm/Sabotage) if unknown
                    if hasattr(self.bridge, 'attack_log') and len(self.bridge.attack_log) > 0:
                        last_attack = self.bridge.attack_log[-1]['attack_type']
                        
                    self.bridge_adapter.attack_detected.emit(last_attack, 0.99)
                        
                elif is_attack:
                    # Normal attack detection before lockdown
                    self.bridge_adapter.attack_detected.emit(
                        telemetry_data.get('attack_type', 0),
                        telemetry_data.get('confidence', 0.0)
                    )
                else:
                    # Clear banner if not compromised and no attack detected
                    self.bridge_adapter.attack_detected.emit(0, 0.0)

            if msg_log:
                self.bridge_adapter.log_message.emit(msg_log, log_type or "system")
        except RuntimeError:
            pass # UI elements are destroyed, silently ignore background updates

    def update_header_data(self):
        """Called by QTimer every 1s to update header status pills."""
        # Update Connection
        if self.bridge.is_connected:
            self.status_pills["CONNECTION"].setText("CONNECTED")
            self.status_pills["CONNECTION"].setStyleSheet(f"color: {SAFE_GREEN}; font-size: 14px; font-weight: bold; border: none;")
        else:
            self.status_pills["CONNECTION"].setText("OFFLINE")
            self.status_pills["CONNECTION"].setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px; font-weight: bold; border: none;")
            
        # Update Mode
        mode = MODE_NAMES.get(self.bridge.current_flight_mode, "UNKNOWN")
        self.status_pills["UAV STATUS"].setText(mode)
        
        # Update Armed State
        armed = getattr(self.bridge, 'state_dict', {}).get('armed', 0) if hasattr(self.bridge, 'state_dict') else 0
        if armed == 1.0:
            self.status_pills["ARMED"].setText("ARMED")
            self.status_pills["ARMED"].setStyleSheet(f"color: {SAFE_GREEN}; font-size: 14px; font-weight: bold; border: none;")
        else:
            self.status_pills["ARMED"].setText("DISARMED")
            self.status_pills["ARMED"].setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px; font-weight: bold; border: none;")
            
        # Update GPS — T9.5: now using live satellite count
        sats = getattr(self.bridge, 'gps_satellites', 0)
        if sats >= 6:
            self.status_pills["GPS"].setText(f"FIX ({sats})")
            self.status_pills["GPS"].setStyleSheet(f"color: {SAFE_GREEN}; font-size: 14px; font-weight: bold; border: none;")
        elif sats > 0:
            self.status_pills["GPS"].setText(f"WEAK ({sats})")
            self.status_pills["GPS"].setStyleSheet(f"color: {WARN_ORANGE}; font-size: 14px; font-weight: bold; border: none;")
        else:
            self.status_pills["GPS"].setText("NO FIX")
            self.status_pills["GPS"].setStyleSheet(f"color: {ALERT_RED}; font-size: 14px; font-weight: bold; border: none;")
            
        # Update Battery — T9.4: now using live battery_pct from SYS_STATUS
        batt = getattr(self.bridge, 'battery_pct', -1)
        if batt < 0:
            self.status_pills["BATTERY"].setText("N/A")
            self.status_pills["BATTERY"].setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px; font-weight: bold; border: none;")
        elif batt <= 20:
            self.status_pills["BATTERY"].setText(f"{batt}%")
            self.status_pills["BATTERY"].setStyleSheet(f"color: {ALERT_RED}; font-size: 14px; font-weight: bold; border: none;")
        elif batt <= 50:
            self.status_pills["BATTERY"].setText(f"{batt}%")
            self.status_pills["BATTERY"].setStyleSheet(f"color: {WARN_ORANGE}; font-size: 14px; font-weight: bold; border: none;")
        else:
            self.status_pills["BATTERY"].setText(f"{batt}%")
            self.status_pills["BATTERY"].setStyleSheet(f"color: {SAFE_GREEN}; font-size: 14px; font-weight: bold; border: none;")
        
        # Update Time
        utc_time = datetime.datetime.utcnow().strftime("%H:%M:%S")
        self.status_pills["TIME (UTC)"].setText(utc_time)
        self.status_pills["TIME (UTC)"].setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")

# ═══════════════════════════════════════════════════
# T10.1 — Global QSS Stylesheet (dark military theme)
# ═══════════════════════════════════════════════════
GLOBAL_QSS = f"""
QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: Arial, sans-serif;
}}
QScrollBar:vertical {{
    border: none;
    background: {PANEL_BG};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_DEFAULT};
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT_CYAN};
}}
QScrollBar:horizontal {{
    border: none;
    background: {PANEL_BG};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_DEFAULT};
    border-radius: 4px;
}}
QComboBox {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 3px;
    padding: 5px;
}}
QComboBox QAbstractItemView {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT_CYAN};
    selection-color: {BG_DARK};
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: {BORDER_DEFAULT};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT_CYAN};
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT_PURPLE};
    border-radius: 3px;
}}
QToolTip {{
    background-color: {CARD_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    padding: 4px;
}}
"""

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # T10.1 — Apply global dark military QSS
    app.setStyleSheet(GLOBAL_QSS)
    app.setFont(QFont("Arial", 10))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
