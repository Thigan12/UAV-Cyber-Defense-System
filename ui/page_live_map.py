import os
import math
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QFrame, QPushButton, QGridLayout)
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage

from ui.theme import *

def calc_rtl_distance(lat, lon, home_lat, home_lon) -> float:
    if lat == 0 or lon == 0 or home_lat == 0 or home_lon == 0:
        return 0.0
    R = 6371.0
    dlat = math.radians(lat - home_lat)
    dlon = math.radians(lon - home_lon)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(home_lat)) * \
        math.cos(math.radians(lat)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class MapInterceptPage(QWebEnginePage):
    """Intercepts console.log from JavaScript to trigger Python actions."""
    def __init__(self, parent=None, callback=None):
        super().__init__(parent)
        self.callback = callback
        
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        if message.startswith("FLY_TO:"):
            if self.callback:
                self.callback(message)
        super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)

class LiveMapPage(QWidget):
    """Live map — Leaflet.js in QWebEngineView, flight path, map controls."""
    fly_command_requested = pyqtSignal(float, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        lbl = QLabel("LIVE MAP & FLIGHT PATH")
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 18px; font-weight: bold;")
        self.main_layout.addWidget(lbl)
        
        self.main_split = QHBoxLayout()
        self.main_layout.addLayout(self.main_split, stretch=1)
        
        # Left: Map
        self.build_map_view()
        
        # Right: Info & Controls
        self.right_panel = QVBoxLayout()
        self.main_split.addLayout(self.right_panel, stretch=1)
        
        self.build_map_info()
        self.build_map_controls()
        self.right_panel.addStretch()
        
        # State
        self.home_lat = 0
        self.home_lon = 0
        self.current_lat = 0
        self.current_lon = 0
        self.showing_rtl = False

    def build_map_view(self):
        self.map_frame = QFrame()
        self.map_frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        map_layout = QVBoxLayout(self.map_frame)
        map_layout.setContentsMargins(0, 0, 0, 0)
        
        self.map_view = QWebEngineView()
        
        # Intercept JS console logs for right-clicks
        self.intercept_page = MapInterceptPage(self.map_view, self.handle_map_command)
        self.map_view.setPage(self.intercept_page)
        
        map_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'map.html'))
        self.map_view.setUrl(QUrl.fromLocalFile(map_path))
        
        map_layout.addWidget(self.map_view)
        self.main_split.addWidget(self.map_frame, stretch=4)

    def build_map_info(self):
        self.info_frame = QFrame()
        self.info_frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        layout = QVBoxLayout(self.info_frame)
        
        lbl_title = QLabel("TELEMETRY INFO")
        lbl_title.setStyleSheet(f"color: {ACCENT_CYAN}; font-size: 12px; font-weight: bold; border: none;")
        layout.addWidget(lbl_title)
        
        self.info_labels = {}
        fields = ["Current Lat", "Current Lon", "Altitude", "Ground Speed", "RTL Distance", "Satellites"]
        
        for field in fields:
            row = QHBoxLayout()
            lbl_name = QLabel(field)
            lbl_name.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; border: none;")
            lbl_val = QLabel("--")
            lbl_val.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px; font-weight: bold; border: none;")
            lbl_val.setAlignment(Qt.AlignRight)
            row.addWidget(lbl_name)
            row.addWidget(lbl_val)
            self.info_labels[field] = lbl_val
            layout.addLayout(row)
            
        self.right_panel.addWidget(self.info_frame)

    def build_map_controls(self):
        self.ctrl_frame = QFrame()
        self.ctrl_frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        layout = QVBoxLayout(self.ctrl_frame)
        
        lbl_title = QLabel("MAP CONTROLS")
        lbl_title.setStyleSheet(f"color: {ACCENT_PURPLE}; font-size: 12px; font-weight: bold; border: none;")
        layout.addWidget(lbl_title)
        
        grid = QGridLayout()
        grid.setSpacing(10)
        
        btn_in = QPushButton("➕ Zoom In")
        btn_in.setStyleSheet(f"background-color: {CARD_BG}; color: {TEXT_PRIMARY}; padding: 8px; border-radius: 3px;")
        btn_in.clicked.connect(lambda: self.map_view.page().runJavaScript("mapZoomIn()"))
        
        btn_out = QPushButton("➖ Zoom Out")
        btn_out.setStyleSheet(f"background-color: {CARD_BG}; color: {TEXT_PRIMARY}; padding: 8px; border-radius: 3px;")
        btn_out.clicked.connect(lambda: self.map_view.page().runJavaScript("mapZoomOut()"))
        
        btn_center = QPushButton("🎯 Center UAV")
        btn_center.setStyleSheet(f"background-color: {CARD_BG}; color: {TEXT_PRIMARY}; padding: 8px; border-radius: 3px;")
        btn_center.clicked.connect(lambda: self.map_view.page().runJavaScript(f"centerUAV({self.current_lat}, {self.current_lon})"))
        
        self.btn_rtl_path = QPushButton("🔴 Toggle RTL Path")
        self.btn_rtl_path.setStyleSheet(f"background-color: {CARD_BG}; color: {TEXT_PRIMARY}; padding: 8px; border-radius: 3px;")
        self.btn_rtl_path.clicked.connect(self.toggle_rtl_path)
        
        grid.addWidget(btn_in, 0, 0)
        grid.addWidget(btn_out, 0, 1)
        grid.addWidget(btn_center, 1, 0, 1, 2)
        grid.addWidget(self.btn_rtl_path, 2, 0, 1, 2)
        
        layout.addLayout(grid)
        self.right_panel.addWidget(self.ctrl_frame)

    def toggle_rtl_path(self):
        self.showing_rtl = not self.showing_rtl
        if self.showing_rtl:
            self.btn_rtl_path.setStyleSheet(f"background-color: {ALERT_RED}; color: white; padding: 8px; border-radius: 3px;")
            self.map_view.page().runJavaScript(f"showRTLPath({self.current_lat}, {self.current_lon}, {self.home_lat}, {self.home_lon})")
        else:
            self.btn_rtl_path.setStyleSheet(f"background-color: {CARD_BG}; color: {TEXT_PRIMARY}; padding: 8px; border-radius: 3px;")
            self.map_view.page().runJavaScript("clearRTLPath()")

    def handle_map_command(self, msg: str):
        """Parse FLY_TO command from Leaflet and emit signal to backend"""
        try:
            coords = msg.replace("FLY_TO:", "").split(",")
            lat = float(coords[0])
            lon = float(coords[1])
            self.fly_command_requested.emit(lat, lon)
        except Exception as e:
            print(f"Map command parse error: {e}")

    def update_map(self, data: dict):
        if 'lat' in data and 'lon' in data:
            self.current_lat = data['lat']
            self.current_lon = data['lon']
            alt = data.get('alt', 0)
            spd = data.get('spd', 0)
            
            if self.home_lat == 0 and self.current_lat != 0:
                self.home_lat = self.current_lat
                self.home_lon = self.current_lon
                self.map_view.page().runJavaScript(f"setHomePosition({self.home_lat}, {self.home_lon})")
            
            # Update Map
            self.map_view.page().runJavaScript(f"updateDronePosition({self.current_lat}, {self.current_lon}, {alt}, {spd})")
            self.map_view.page().runJavaScript(f"addPathPoint({self.current_lat}, {self.current_lon})")
            
            if self.showing_rtl:
                self.map_view.page().runJavaScript(f"showRTLPath({self.current_lat}, {self.current_lon}, {self.home_lat}, {self.home_lon})")

            # Update Info Panel
            self.info_labels["Current Lat"].setText(f"{self.current_lat:.6f}°")
            self.info_labels["Current Lon"].setText(f"{self.current_lon:.6f}°")
            self.info_labels["Altitude"].setText(f"{alt:.1f} m")
            self.info_labels["Ground Speed"].setText(f"{spd:.1f} m/s")
            
            dist = calc_rtl_distance(self.current_lat, self.current_lon, self.home_lat, self.home_lon)
            self.info_labels["RTL Distance"].setText(f"{dist:.2f} km")
            
            sat = data.get('satellites', 12) # Fallback to 12 if not provided
            self.info_labels["Satellites"].setText(str(sat))
            
            # Show attack zone if under attack
            is_attack = data.get('is_attack', False)
            if is_attack:
                self.map_view.page().runJavaScript(f"showAttackZone({self.current_lat}, {self.current_lon})")
            else:
                self.map_view.page().runJavaScript("clearAttackZone()")
