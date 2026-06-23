import collections
import numpy as np
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ui.theme import *


class CircularGaugeFull(QWidget):
    """Custom circular gauge for confidence score (Full circle)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 150)
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
        pen_bg = QPen(QColor(BORDER_DEFAULT), 12, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(x, y, size, size, 0, 360 * 16)
        
        # Draw foreground progress
        pen_fg = QPen(QColor(self.color), 12, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen_fg)
        span_angle = int(-self.value * 360 * 16) # Negative for clockwise
        painter.drawArc(x, y, size, size, 90 * 16, span_angle)
        
        # Draw text
        painter.setPen(QColor(self.color))
        font = QFont("Arial", 22, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{self.value * 100:.1f}%")


class AIDetectionPage(QWidget):
    """AI detection — prediction display, confidence gauge, consensus, class bars, feature importance."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        lbl = QLabel("AI DETECTION & CLASSIFICATION")
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 18px; font-weight: bold;")
        self.main_layout.addWidget(lbl)
        
        # Top Half Layout
        self.top_layout = QHBoxLayout()
        self.main_layout.addLayout(self.top_layout, stretch=1)
        
        # T4.1 Current Prediction
        self.build_prediction_panel()
        
        # T4.2 Confidence Gauge
        self.build_gauge_panel()
        
        # T4.3 & T4.4 Consensus and Probabilities
        self.build_consensus_and_probs_panel()
        
        # Bottom Half Layout
        self.bottom_layout = QHBoxLayout()
        self.main_layout.addLayout(self.bottom_layout, stretch=2)
        
        # T4.5 & T4.6 Graphs
        self.build_graphs_panel()
        
        # T4.7 Recent Predictions Table
        self.build_predictions_table()
        
        # State variables
        self.conf_history = collections.deque(maxlen=60)
        self.time_history = collections.deque(maxlen=60)

    def build_prediction_panel(self):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        layout = QVBoxLayout(frame)
        
        lbl_title = QLabel("CURRENT PREDICTION")
        lbl_title.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; font-weight: bold; border: none;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)
        
        self.lbl_pred = QLabel("NORMAL")
        self.lbl_pred.setStyleSheet(f"color: {SAFE_GREEN}; font-size: 28px; font-weight: bold; border: none;")
        self.lbl_pred.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_pred)
        
        self.lbl_badge = QLabel("NORMAL FLIGHT")
        self.lbl_badge.setStyleSheet(f"background-color: #004d00; color: {SAFE_GREEN}; padding: 10px; border-radius: 5px; font-weight: bold;")
        self.lbl_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_badge)
        
        self.top_layout.addWidget(frame, stretch=1)

    def build_gauge_panel(self):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        layout = QVBoxLayout(frame)
        
        lbl_title = QLabel("CONFIDENCE SCORE")
        lbl_title.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; font-weight: bold; border: none;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)
        
        self.gauge = CircularGaugeFull()
        layout.addWidget(self.gauge, alignment=Qt.AlignCenter)
        
        self.lbl_risk = QLabel("LOW")
        self.lbl_risk.setStyleSheet(f"color: {SAFE_GREEN}; font-size: 14px; font-weight: bold; border: none;")
        self.lbl_risk.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_risk)
        
        self.top_layout.addWidget(frame, stretch=1)

    def build_consensus_and_probs_panel(self):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        layout = QVBoxLayout(frame)
        
        # Consensus
        lbl_cons = QLabel("CONSENSUS (3-TICK RULE)")
        lbl_cons.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; font-weight: bold; border: none;")
        lbl_cons.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_cons)
        
        cons_layout = QHBoxLayout()
        cons_layout.setAlignment(Qt.AlignCenter)
        self.cons_dots = []
        for _ in range(3):
            dot = QLabel()
            dot.setFixedSize(20, 20)
            dot.setStyleSheet(f"background-color: {BORDER_DEFAULT}; border-radius: 10px;")
            cons_layout.addWidget(dot)
            self.cons_dots.append(dot)
            
        layout.addLayout(cons_layout)
        
        self.lbl_cons_text = QLabel("WAITING FOR CONSENSUS")
        self.lbl_cons_text.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; font-weight: bold; border: none;")
        self.lbl_cons_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_cons_text)
        
        # Probabilities
        lbl_probs = QLabel("ATTACK CLASSES")
        lbl_probs.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; font-weight: bold; border: none; margin-top: 10px;")
        layout.addWidget(lbl_probs)
        
        self.prob_bars = {}
        for i in range(5):
            row = QHBoxLayout()
            lbl_name = QLabel(CLASS_NAMES[i])
            lbl_name.setStyleSheet(f"color: {CLASS_COLOURS[i]}; font-size: 11px; border: none;")
            lbl_name.setFixedWidth(80)
            
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            bar.setStyleSheet(f"""
                QProgressBar {{ border: none; background-color: {BORDER_DEFAULT}; border-radius: 4px; }}
                QProgressBar::chunk {{ background-color: {CLASS_COLOURS[i]}; border-radius: 4px; }}
            """)
            bar.setValue(0)
            
            lbl_val = QLabel("0.0%")
            lbl_val.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; border: none;")
            lbl_val.setFixedWidth(40)
            lbl_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            row.addWidget(lbl_name)
            row.addWidget(bar)
            row.addWidget(lbl_val)
            self.prob_bars[i] = (bar, lbl_val)
            layout.addLayout(row)
            
        self.top_layout.addWidget(frame, stretch=2)

    def build_graphs_panel(self):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        layout = QVBoxLayout(frame)
        
        self.fig = Figure(figsize=(6, 6), facecolor=PANEL_BG)
        self.canvas = FigureCanvas(self.fig)
        
        # T4.5 Confidence Over Time
        self.ax_conf = self.fig.add_subplot(2, 1, 1)
        self.ax_conf.set_facecolor(BG_DARK)
        self.ax_conf.tick_params(colors=TEXT_MUTED, labelsize=8)
        self.ax_conf.spines['bottom'].set_color(BORDER_DEFAULT)
        self.ax_conf.spines['top'].set_visible(False)
        self.ax_conf.spines['right'].set_visible(False)
        self.ax_conf.spines['left'].set_color(BORDER_DEFAULT)
        self.ax_conf.set_title("CONFIDENCE OVER TIME", color=TEXT_PRIMARY, fontsize=10, loc='left')
        self.ax_conf.set_ylim(-5, 105)
        self.line_conf, = self.ax_conf.plot([], [], color=ALERT_RED, linewidth=2)
        
        # T4.6 Feature Importance (Static)
        self.ax_feat = self.fig.add_subplot(2, 1, 2)
        self.ax_feat.set_facecolor(BG_DARK)
        self.ax_feat.tick_params(colors=TEXT_MUTED, labelsize=8)
        self.ax_feat.spines['bottom'].set_color(BORDER_DEFAULT)
        self.ax_feat.spines['top'].set_visible(False)
        self.ax_feat.spines['right'].set_visible(False)
        self.ax_feat.spines['left'].set_color(BORDER_DEFAULT)
        self.ax_feat.set_title("FEATURE IMPORTANCE (TOP 8)", color=TEXT_PRIMARY, fontsize=10, loc='left')
        
        features = ['vz', 'alt_trend', 'armed_state', 'rollspeed', 
                    'servo1_raw', 'alt_delta', 'gps_jump_magnitude', 'rc_chan1_raw']
        importance = [0.06, 0.07, 0.08, 0.09, 0.11, 0.12, 0.18, 0.23]
        
        bars = self.ax_feat.barh(features, importance, color=ACCENT_PURPLE)
        
        # Add labels to bars
        for bar in bars:
            width = bar.get_width()
            self.ax_feat.text(width + 0.01, bar.get_y() + bar.get_height()/2, 
                              f'{width:.2f}', va='center', ha='left', color=TEXT_PRIMARY, fontsize=8)
                              
        self.ax_feat.set_xlim(0, 0.3)
        
        self.fig.tight_layout(pad=2.0)
        layout.addWidget(self.canvas)
        
        self.bottom_layout.addWidget(frame, stretch=1)

    def build_predictions_table(self):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        layout = QVBoxLayout(frame)
        
        lbl = QLabel("RECENT PREDICTIONS")
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold;")
        layout.addWidget(lbl)
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["TIME (UTC)", "PREDICTION", "CONFIDENCE", "CONSENSUS", "ACTION"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: transparent; color: {TEXT_PRIMARY}; border: none; gridline-color: {BORDER_DEFAULT}; }}
            QHeaderView::section {{ background-color: {CARD_BG}; color: {TEXT_MUTED}; font-weight: bold; border: none; padding: 5px; }}
        """)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.table)
        self.bottom_layout.addWidget(frame, stretch=1)

    # --- Slot Updates ---
    
    def update_prediction_from_data(self, data: dict):
        """Called at 2Hz by telemetry_heavy signal. Dispatches to specific update methods."""
        pred_class = data.get('attack_type', 0)
        confidence = data.get('confidence', 0.0)
        self.update_prediction(pred_class, confidence)
        
        pred_array = data.get('pred_array', [0.0] * 5)
        if pred_array:
            self.update_class_bars(np.array(pred_array))
            
        consensus = data.get('consensus', 0)
        self.update_consensus(consensus)
        
    def update_prediction(self, pred_class: int, confidence: float):
        self.lbl_pred.setText(CLASS_NAMES.get(pred_class, "UNKNOWN").upper())
        self.lbl_pred.setStyleSheet(f"color: {CLASS_COLOURS.get(pred_class, SAFE_GREEN)}; font-size: 28px; font-weight: bold; border: none;")
        
        if pred_class == 0:
            self.lbl_badge.setText("NORMAL FLIGHT")
            self.lbl_badge.setStyleSheet(f"background-color: #004d00; color: {SAFE_GREEN}; padding: 10px; border-radius: 5px; font-weight: bold;")
            self.lbl_risk.setText("LOW RISK")
            self.lbl_risk.setStyleSheet(f"color: {SAFE_GREEN}; font-size: 14px; font-weight: bold; border: none;")
            self.gauge.set_value(confidence, SAFE_GREEN)
        else:
            self.lbl_badge.setText("⚠ ATTACK DETECTED")
            self.lbl_badge.setStyleSheet(f"background-color: #4d0000; color: {ALERT_RED}; padding: 10px; border-radius: 5px; font-weight: bold;")
            
            if confidence >= 0.9:
                risk_color = ALERT_RED
                risk_text = "CRITICAL RISK"
            elif confidence >= 0.7:
                risk_color = WARN_ORANGE
                risk_text = "MEDIUM RISK"
            else:
                risk_color = WARN_YELLOW
                risk_text = "LOW RISK"
                
            self.lbl_risk.setText(risk_text)
            self.lbl_risk.setStyleSheet(f"color: {risk_color}; font-size: 14px; font-weight: bold; border: none;")
            self.gauge.set_value(confidence, risk_color)
            
        self.update_confidence_graph(confidence)

    def update_consensus(self, tick_count: int):
        for i, dot in enumerate(self.cons_dots):
            if i < tick_count:
                dot.setStyleSheet(f"background-color: {SAFE_GREEN}; border-radius: 10px;")
            else:
                dot.setStyleSheet(f"background-color: {BORDER_DEFAULT}; border-radius: 10px;")
                
        if tick_count >= 3:
            self.lbl_cons_text.setText("CONSENSUS REACHED")
            self.lbl_cons_text.setStyleSheet(f"color: {SAFE_GREEN}; font-size: 12px; font-weight: bold; border: none;")
        else:
            self.lbl_cons_text.setText(f"WAITING... ({tick_count}/3)")
            self.lbl_cons_text.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; font-weight: bold; border: none;")

    def update_class_bars(self, pred_array: np.ndarray):
        for i in range(5):
            prob = pred_array[i] * 100
            self.prob_bars[i][0].setValue(int(prob))
            self.prob_bars[i][1].setText(f"{prob:.1f}%")

    def update_confidence_graph(self, confidence: float):
        self.time_history.append(len(self.time_history))
        self.conf_history.append(confidence * 100)
        
        self.line_conf.set_data(list(self.time_history), list(self.conf_history))
        self.ax_conf.set_xlim(max(0, self.time_history[-1] - 60), max(60, self.time_history[-1]))
        
        self.canvas.draw_idle()

    def add_prediction_row(self, time_str, pred_class, confidence, consensus, action):
        row = self.table.rowCount()
        # Keep rolling last 10
        if row >= 10:
            self.table.removeRow(0)
            row = 9
            
        self.table.insertRow(row)
        
        # Time
        self.table.setItem(row, 0, QTableWidgetItem(time_str))
        
        # Prediction
        item_pred = QTableWidgetItem(CLASS_NAMES.get(pred_class, "Unknown"))
        item_pred.setForeground(QColor(CLASS_COLOURS.get(pred_class, SAFE_GREEN)))
        self.table.setItem(row, 1, item_pred)
        
        # Confidence
        self.table.setItem(row, 2, QTableWidgetItem(f"{confidence*100:.1f}%"))
        
        # Consensus
        self.table.setItem(row, 3, QTableWidgetItem(f"{consensus}/3"))
        
        # Action
        self.table.setItem(row, 4, QTableWidgetItem(action))
