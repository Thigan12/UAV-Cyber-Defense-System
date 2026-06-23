import json
import os
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QFrame, QLineEdit, QSlider, QPushButton, 
                             QFileDialog, QMessageBox, QGridLayout, QComboBox, QCheckBox)
from PyQt5.QtCore import Qt

from ui.theme import *

class CardPanel(QFrame):
    def __init__(self, title, color=ACCENT_CYAN):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {PANEL_BG}; 
                border: 1px solid {BORDER_DEFAULT}; 
                border-radius: 8px;
            }}
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold; border: none; letter-spacing: 1px;")
        self.layout.addWidget(lbl)
        
        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(15)
        self.grid.setHorizontalSpacing(20)
        self.layout.addLayout(self.grid)

class SettingsPage(QWidget):
    """Settings — connection config, model config, threshold sliders."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        lbl = QLabel("SYSTEM CONFIGURATION")
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 800; letter-spacing: 2px;")
        header_layout.addWidget(lbl)
        header_layout.addStretch()
        
        self.btn_save = QPushButton("💾 APPLY & RESTART PROTOCOLS")
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {SAFE_GREEN}; color: {BG_DARK}; 
                padding: 10px 20px; border-radius: 5px; 
                font-weight: bold; font-size: 13px;
            }}
            QPushButton:hover {{ background-color: #00ff88; }}
        """)
        self.btn_save.clicked.connect(self.save_settings)
        header_layout.addWidget(self.btn_save)
        
        self.main_layout.addLayout(header_layout)
        
        # Panels Layout
        panels_layout = QHBoxLayout()
        self.left_col = QVBoxLayout()
        self.right_col = QVBoxLayout()
        panels_layout.addLayout(self.left_col, 1)
        panels_layout.addLayout(self.right_col, 1)
        self.main_layout.addLayout(panels_layout)
        
        self.build_connection_settings()
        self.build_ai_settings()
        self.build_zero_trust_settings()
        
        self.main_layout.addStretch()
        self.load_settings()

    def create_label(self, text, tooltip=""):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: bold; border: none; font-size: 12px;")
        if tooltip:
            lbl.setToolTip(tooltip)
        return lbl

    def create_input(self, text=""):
        inp = QLineEdit(text)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_DARK}; color: {TEXT_PRIMARY}; 
                padding: 10px; border: 1px solid {BORDER_DEFAULT}; 
                border-radius: 4px; font-family: monospace;
            }}
            QLineEdit:focus {{ border: 1px solid {ACCENT_CYAN}; }}
        """)
        return inp

    def create_slider(self, min_v, max_v, default_v, label_updater):
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(default_v)
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ border: 1px solid {BORDER_DEFAULT}; height: 6px; background: {BG_DARK}; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: {ACCENT_PURPLE}; width: 14px; margin: -4px 0; border-radius: 7px; }}
        """)
        slider.valueChanged.connect(label_updater)
        return slider

    def build_connection_settings(self):
        panel = CardPanel("COMMUNICATION LINK", ACCENT_CYAN)
        
        self.inp_url = self.create_input("udp:127.0.0.1:14550")
        self.btn_reconnect = QPushButton("🔄 Reinitialize")
        self.btn_reconnect.setStyleSheet(f"background-color: {ACCENT_CYAN}; color: {BG_DARK}; padding: 10px; border-radius: 4px; font-weight: bold;")
        
        self.combo_rate = QComboBox()
        self.combo_rate.addItems(["10 Hz (Standard)", "20 Hz (High Performance)", "50 Hz (Extreme)"])
        self.combo_rate.setStyleSheet(f"background-color: {BG_DARK}; color: {TEXT_PRIMARY}; padding: 8px; border: 1px solid {BORDER_DEFAULT}; border-radius: 4px;")
        
        panel.grid.addWidget(self.create_label("MAVLink Interface URI:"), 0, 0)
        panel.grid.addWidget(self.inp_url, 0, 1)
        panel.grid.addWidget(self.btn_reconnect, 0, 2)
        
        panel.grid.addWidget(self.create_label("Telemetry Polling Rate:"), 1, 0)
        panel.grid.addWidget(self.combo_rate, 1, 1, 1, 2)
        
        self.left_col.addWidget(panel)

    def build_ai_settings(self):
        panel = CardPanel("INTRUSION DETECTION CORE", ACCENT_PURPLE)
        
        self.inp_model = self.create_input("lstm_uav_v2.h5")
        btn_browse_model = QPushButton("Browse")
        btn_browse_model.setStyleSheet(f"background-color: {BORDER_DEFAULT}; color: {TEXT_PRIMARY}; padding: 10px; border-radius: 4px;")
        btn_browse_model.clicked.connect(lambda: self.browse_file(self.inp_model, "HDF5 Files (*.h5)"))
        
        self.inp_scaler = self.create_input("scaler_v2.pkl")
        btn_browse_scaler = QPushButton("Browse")
        btn_browse_scaler.setStyleSheet(f"background-color: {BORDER_DEFAULT}; color: {TEXT_PRIMARY}; padding: 10px; border-radius: 4px;")
        btn_browse_scaler.clicked.connect(lambda: self.browse_file(self.inp_scaler, "Pickle Files (*.pkl)"))
        
        panel.grid.addWidget(self.create_label("AI Model File (.h5):"), 0, 0)
        panel.grid.addWidget(self.inp_model, 0, 1)
        panel.grid.addWidget(btn_browse_model, 0, 2)
        
        panel.grid.addWidget(self.create_label("Scaler Profile (.pkl):"), 1, 0)
        panel.grid.addWidget(self.inp_scaler, 1, 1)
        panel.grid.addWidget(btn_browse_scaler, 1, 2)
        
        self.val_conf = self.create_label("0.95")
        self.val_conf.setStyleSheet(f"color: {ACCENT_PURPLE}; font-weight: bold; font-size: 14px; border: none;")
        self.slider_conf = self.create_slider(0, 100, 95, lambda v: self.val_conf.setText(f"{v/100:.2f}"))
        panel.grid.addWidget(self.create_label("Confidence Threshold:"), 2, 0)
        panel.grid.addWidget(self.slider_conf, 2, 1)
        panel.grid.addWidget(self.val_conf, 2, 2)
        
        self.val_warmup = self.create_label("90s")
        self.val_warmup.setStyleSheet(f"color: {ACCENT_PURPLE}; font-weight: bold; font-size: 14px; border: none;")
        self.slider_warmup = self.create_slider(10, 300, 90, lambda v: self.val_warmup.setText(f"{v}s"))
        panel.grid.addWidget(self.create_label("AI Warmup Delay:"), 3, 0)
        panel.grid.addWidget(self.slider_warmup, 3, 1)
        panel.grid.addWidget(self.val_warmup, 3, 2)
        
        self.val_ticks = self.create_label("3")
        self.val_ticks.setStyleSheet(f"color: {ACCENT_PURPLE}; font-weight: bold; font-size: 14px; border: none;")
        self.slider_ticks = self.create_slider(1, 10, 3, lambda v: self.val_ticks.setText(f"{v}"))
        panel.grid.addWidget(self.create_label("Consensus Ticks (Smoothing):"), 4, 0)
        panel.grid.addWidget(self.slider_ticks, 4, 1)
        panel.grid.addWidget(self.val_ticks, 4, 2)
        
        self.left_col.addWidget(panel)

    def build_zero_trust_settings(self):
        panel = CardPanel("ZERO-TRUST ENFORCEMENT", ALERT_RED)
        
        self.chk_auto_mitigate = QCheckBox("Enable Autonomous Mitigation (RTL / LAND)")
        self.chk_auto_mitigate.setChecked(True)
        self.chk_auto_mitigate.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold; font-size: 13px; spacing: 10px; border: none;")
        
        self.chk_gps_failsafe = QCheckBox("Enable IMU-Based Dead Reckoning on GPS Loss")
        self.chk_gps_failsafe.setChecked(True)
        self.chk_gps_failsafe.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold; font-size: 13px; spacing: 10px; border: none;")
        
        self.chk_operator_lock = QCheckBox("Lock Non-Safety Operator Commands during Compromise")
        self.chk_operator_lock.setChecked(True)
        self.chk_operator_lock.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold; font-size: 13px; spacing: 10px; border: none;")
        
        panel.layout.addWidget(self.chk_auto_mitigate)
        panel.layout.addWidget(self.chk_gps_failsafe)
        panel.layout.addWidget(self.chk_operator_lock)
        
        self.right_col.addWidget(panel)
        self.right_col.addStretch()

    def browse_file(self, line_edit, filter_str):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select File", "", filter_str)
        if filepath:
            line_edit.setText(filepath)

    def save_settings(self):
        settings = {
            "mavlink_url": self.inp_url.text(),
            "model_path": self.inp_model.text(),
            "scaler_path": self.inp_scaler.text(),
            "confidence_threshold": self.slider_conf.value() / 100.0,
            "warmup_seconds": self.slider_warmup.value(),
            "consensus_ticks": self.slider_ticks.value(),
            "telemetry_rate": self.combo_rate.currentIndex(),
            "auto_mitigate": self.chk_auto_mitigate.isChecked(),
            "gps_failsafe": self.chk_gps_failsafe.isChecked(),
            "operator_lock": self.chk_operator_lock.isChecked()
        }
        
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config.json'))
        with open(config_path, 'w') as f:
            json.dump(settings, f, indent=4)
            
        QMessageBox.information(self, "Protocols Applied", "Settings have been successfully applied and written to config.json. Engine restarts may be required for URI changes.")

    def load_settings(self):
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config.json'))
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    settings = json.load(f)
                    
                self.inp_url.setText(settings.get("mavlink_url", "udp:127.0.0.1:14550"))
                self.inp_model.setText(settings.get("model_path", "lstm_uav_v2.h5"))
                self.inp_scaler.setText(settings.get("scaler_path", "scaler_v2.pkl"))
                self.slider_conf.setValue(int(settings.get("confidence_threshold", 0.95) * 100))
                self.slider_warmup.setValue(settings.get("warmup_seconds", 90))
                self.slider_ticks.setValue(settings.get("consensus_ticks", 3))
                self.combo_rate.setCurrentIndex(settings.get("telemetry_rate", 0))
                self.chk_auto_mitigate.setChecked(settings.get("auto_mitigate", True))
                self.chk_gps_failsafe.setChecked(settings.get("gps_failsafe", True))
                self.chk_operator_lock.setChecked(settings.get("operator_lock", True))
            except Exception:
                pass
