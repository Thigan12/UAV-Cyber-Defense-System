import collections
import math
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QFrame, QGridLayout)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ui.theme import *

def calc_rtl_distance(lat, lon, home_lat, home_lon) -> float:
    """Haversine formula to calculate distance between two coordinates in km"""
    if lat == 0 or lon == 0 or home_lat == 0 or home_lon == 0:
        return 0.0
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat - home_lat)
    dlon = math.radians(lon - home_lon)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(home_lat)) * \
        math.cos(math.radians(lat)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class MetricCard(QFrame):
    def __init__(self, title, unit=""):
        super().__init__()
        self.setStyleSheet(f"background-color: {CARD_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_title = QLabel(title.upper())
        lbl_title.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: bold; border: none;")
        
        self.lbl_val = QLabel(f"-- {unit}".strip())
        self.lbl_val.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 24px; font-weight: bold; border: none;")
        self.lbl_val.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(lbl_title)
        layout.addWidget(self.lbl_val, alignment=Qt.AlignCenter)
        
        self.unit = unit

    def set_value(self, value_str):
        if self.unit:
            self.lbl_val.setText(f"{value_str} {self.unit}")
        else:
            self.lbl_val.setText(value_str)

class TelemetryPage(QWidget):
    """Live telemetry — metric cards, scrolling graphs, flight data."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        # Header title
        lbl = QLabel("LIVE TELEMETRY")
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 18px; font-weight: bold;")
        self.main_layout.addWidget(lbl)
        
        # T3.1 Top Metrics Row
        self.top_metrics_layout = QHBoxLayout()
        self.top_metrics_layout.setSpacing(10)
        
        self.cards = {}
        top_cards = [
            ("Altitude", "m"), ("Ground Speed", "m/s"), ("Climb Rate", "m/s"), 
            ("Heading", "°"), ("Battery", "%"), ("GPS Satellites", "")
        ]
        
        for title, unit in top_cards:
            card = MetricCard(title, unit)
            self.cards[title] = card
            self.top_metrics_layout.addWidget(card)
            
        self.main_layout.addLayout(self.top_metrics_layout)
        
        # T3.2 Three Live Scrolling Graphs
        self.build_telemetry_graphs()
        
        # T3.3 Bottom Metrics Row
        self.bottom_metrics_layout = QHBoxLayout()
        self.bottom_metrics_layout.setSpacing(10)
        
        bottom_cards = [
            ("Latitude", "°"), ("Longitude", "°"), ("RTL Distance", "km"), 
            ("Air Speed", "m/s"), ("Throttle", "%"), ("Flight Mode", ""), 
            ("Armed State", "")
        ]
        
        for title, unit in bottom_cards:
            card = MetricCard(title, unit)
            self.cards[title] = card
            self.bottom_metrics_layout.addWidget(card)
            
        self.main_layout.addLayout(self.bottom_metrics_layout)
        
        # Store home location for RTL distance calculation
        self.home_lat = 0
        self.home_lon = 0

    def build_telemetry_graphs(self):
        self.graph_frame = QFrame()
        self.graph_frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        graph_layout = QVBoxLayout(self.graph_frame)
        
        self.fig = Figure(figsize=(8, 6), facecolor=PANEL_BG)
        self.canvas = FigureCanvas(self.fig)
        
        self.axs = []
        titles = ["Altitude (m)", "Ground Speed (m/s)", "Climb Rate (m/s)"]
        colors = [SAFE_GREEN, ACCENT_CYAN, WARN_YELLOW]
        
        for i in range(3):
            ax = self.fig.add_subplot(3, 1, i+1)
            ax.set_facecolor(BG_DARK)
            ax.tick_params(colors=TEXT_MUTED, labelsize=9)
            ax.spines['bottom'].set_color(BORDER_DEFAULT)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color(BORDER_DEFAULT)
            ax.set_title(titles[i], color=TEXT_PRIMARY, fontsize=10, loc='left')
            self.axs.append({"ax": ax, "color": colors[i], "line": None})
            
        self.fig.tight_layout(pad=2.0)
        graph_layout.addWidget(self.canvas)
        
        self.main_layout.addWidget(self.graph_frame, stretch=1)
        
        self.time_data = collections.deque(maxlen=60)
        self.graph_data = [collections.deque(maxlen=60) for _ in range(3)]
        self._graph_tick = 0

    def update_metrics(self, data: dict):
        """Called via signal to update all metrics and graphs."""
        
        # Capture home location if not set
        if self.home_lat == 0 and data.get('lat', 0) != 0:
            self.home_lat = data.get('lat')
            self.home_lon = data.get('lon')

        # Update Top Cards
        if 'alt' in data: self.cards["Altitude"].set_value(f"{data['alt']:.1f}")
        if 'spd' in data: self.cards["Ground Speed"].set_value(f"{data['spd']:.1f}")
        
        # Climb rate would normally come from vz, spoofing it from alt for now if vz is not passed
        climb_rate = data.get('vz', 0.0) 
        self.cards["Climb Rate"].set_value(f"{climb_rate:.1f}")
        
        if 'heading' in data: self.cards["Heading"].set_value(f"{data['heading']}")
        self.cards["Battery"].set_value("100") # Hardcoded for now
        self.cards["GPS Satellites"].set_value("12") # Hardcoded for now
        
        # Update Bottom Cards
        if 'lat' in data: 
            self.cards["Latitude"].set_value(f"{data['lat']:.6f}")
            self.cards["Longitude"].set_value(f"{data['lon']:.6f}")
            dist = calc_rtl_distance(data['lat'], data['lon'], self.home_lat, self.home_lon)
            self.cards["RTL Distance"].set_value(f"{dist:.2f}")
            
        self.cards["Air Speed"].set_value(f"{data.get('spd', 0):.1f}") # Fallback to groundspeed
        self.cards["Throttle"].set_value("68") # Placeholder
        
        # Mode and Armed
        self.cards["Flight Mode"].set_value(MODE_NAMES.get(data.get('flight_mode', 0), "UNKNOWN"))
        armed_state = data.get('armed', 0)
        if armed_state:
            self.cards["Armed State"].set_value("ARMED")
            self.cards["Armed State"].lbl_val.setStyleSheet(f"color: {SAFE_GREEN}; font-size: 24px; font-weight: bold; border: none;")
        else:
            self.cards["Armed State"].set_value("DISARMED")
            self.cards["Armed State"].lbl_val.setStyleSheet(f"color: {ALERT_RED}; font-size: 24px; font-weight: bold; border: none;")

        # Update Graphs
        if 'alt' in data:
            self.time_data.append(self._graph_tick)
            self._graph_tick += 1
            
            self.graph_data[0].append(data['alt'])
            self.graph_data[1].append(data['spd'])
            self.graph_data[2].append(climb_rate)
            
            for i, deque_data in enumerate(self.graph_data):
                if len(deque_data) > 0:
                    if self.axs[i]["line"] is None:
                        self.axs[i]["line"], = self.axs[i]["ax"].plot(list(self.time_data), list(deque_data), color=self.axs[i]["color"], linewidth=2)
                    else:
                        self.axs[i]["line"].set_data(list(self.time_data), list(deque_data))
                    
                    self.axs[i]["ax"].set_xlim(max(0, self.time_data[-1] - 60), max(60, self.time_data[-1]))
                    
                    min_y = min(deque_data)
                    max_y = max(deque_data)
                    margin = (max_y - min_y) * 0.1 if max_y != min_y else 1.0
                    self.axs[i]["ax"].set_ylim(min_y - margin, max_y + margin)
            
            self.canvas.draw_idle()
