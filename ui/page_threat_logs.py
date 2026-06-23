import csv
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
                             QComboBox, QPushButton, QDateEdit, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QBrush

from ui.theme import *


class ThreatLogsPage(QWidget):
    """Threat logs — filterable table, colour-coded rows, CSV export."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        lbl = QLabel("THREAT LOGS & HISTORY")
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 18px; font-weight: bold;")
        self.main_layout.addWidget(lbl)
        
        self.attack_log = [] # T6.1 Local data store
        
        # Throttle state variables (Bug 10 fix: must be in __init__)
        self.last_logged_class = 0
        self.last_log_time = 0
        
        self.build_filter_controls()
        self.build_log_table()
        
        # Add some mock data for demonstration if empty
        # self._add_mock_data()

    def build_filter_controls(self):
        """T6.3 — Filter Controls"""
        self.filter_frame = QFrame()
        self.filter_frame.setStyleSheet(f"background-color: {PANEL_BG}; border: 1px solid {BORDER_DEFAULT}; border-radius: 5px;")
        filter_layout = QHBoxLayout(self.filter_frame)
        
        lbl_type = QLabel("Filter by Type:")
        lbl_type.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: bold; border: none;")
        self.combo_type = QComboBox()
        self.combo_type.addItems(["All", "RC Hijack", "Mode Forcing", "GPS Spoofing", "Disarm", "Normal"])
        self.combo_type.setStyleSheet(f"background-color: {CARD_BG}; color: {TEXT_PRIMARY}; padding: 5px; border-radius: 3px;")
        self.combo_type.currentTextChanged.connect(self.apply_filters)
        
        lbl_date = QLabel("Filter by Date:")
        lbl_date.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: bold; border: none;")
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setStyleSheet(f"background-color: {CARD_BG}; color: {TEXT_PRIMARY}; padding: 5px; border-radius: 3px;")
        # Commenting out strict date filter connection for now to allow all data to show by default
        # self.date_edit.dateChanged.connect(self.apply_filters)
        
        btn_clear_filters = QPushButton("Clear Filters")
        btn_clear_filters.setStyleSheet(f"background-color: {CARD_BG}; color: {TEXT_PRIMARY}; padding: 5px 15px; border-radius: 3px;")
        btn_clear_filters.clicked.connect(self.clear_filters)
        
        self.btn_export = QPushButton("📥 Export CSV")
        self.btn_export.setStyleSheet(f"background-color: {ACCENT_CYAN}; color: {BG_DARK}; padding: 5px 15px; border-radius: 3px; font-weight: bold;")
        self.btn_export.clicked.connect(self.export_to_csv)
        
        filter_layout.addWidget(lbl_type)
        filter_layout.addWidget(self.combo_type)
        filter_layout.addSpacing(20)
        filter_layout.addWidget(lbl_date)
        filter_layout.addWidget(self.date_edit)
        filter_layout.addWidget(btn_clear_filters)
        filter_layout.addStretch()
        filter_layout.addWidget(self.btn_export)
        
        self.main_layout.addWidget(self.filter_frame)

    def build_log_table(self):
        """T6.2 — Threat Log Table"""
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["TIME (UTC)", "ATTACK TYPE", "CONFIDENCE", "LOCATION", "ALTITUDE (m)", "ACTION TAKEN", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: {PANEL_BG}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_DEFAULT}; gridline-color: {BORDER_DEFAULT}; border-radius: 5px; }}
            QHeaderView::section {{ background-color: {CARD_BG}; color: {TEXT_MUTED}; font-weight: bold; border: none; padding: 10px; border-bottom: 1px solid {BORDER_DEFAULT}; }}
            QTableWidget::item {{ padding: 5px; }}
        """)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(False)
        
        self.main_layout.addWidget(self.table, stretch=1)

    def log_attack(self, data: dict):
        """Called by signal to add a new row."""
        attack_class = data.get('attack_type', 0)
        if attack_class == 0:
            self.last_logged_class = 0
            return # Don't log normal flights here
            
        import time
        current_time = time.time()
        
        # Throttle: Only log if it's a new attack class, or 10 seconds have passed since last log
        if attack_class == self.last_logged_class and (current_time - self.last_log_time) < 10:
            return
            
        self.last_logged_class = attack_class
        self.last_log_time = current_time
        
        name = CLASS_NAMES.get(attack_class, "Unknown")
        conf = data.get('confidence', 0.0)
        lat = data.get('lat', 0.0)
        lon = data.get('lon', 0.0)
        alt = data.get('alt', 0.0)
        
        # Save to local store
        log_entry = {
            "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "attack_type": name,
            "confidence": f"{conf*100:.1f}",
            "lat": lat,
            "lon": lon,
            "altitude": alt,
            "action": "RTL Activated",
            "status": "Mitigated"
        }
        self.attack_log.append(log_entry)
        
        # Add to UI table
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        bg_colors = {
            1: QColor("#3d0000"), # RC Hijack
            2: QColor("#3d1a00"), # Mode Forcing
            3: QColor("#2d2d00"), # GPS Spoofing
            4: QColor("#3d003d"), # Disarm
            0: QColor("#002d00")  # Normal
        }
        bg_brush = QBrush(bg_colors.get(attack_class, QColor(PANEL_BG)))
        
        items = [
            QTableWidgetItem(log_entry["time"]),
            QTableWidgetItem(log_entry["attack_type"]),
            QTableWidgetItem(f"{log_entry['confidence']}%"),
            QTableWidgetItem(f"{lat:.4f}, {lon:.4f}"),
            QTableWidgetItem(f"{alt:.1f}"),
            QTableWidgetItem(log_entry["action"]),
            QTableWidgetItem(log_entry["status"])
        ]
        
        # Color specific texts
        items[1].setForeground(QBrush(QColor(CLASS_COLOURS.get(attack_class, SAFE_GREEN))))
        items[6].setForeground(QBrush(QColor(ALERT_RED))) # Mitigated status in red for urgency
        
        for i, item in enumerate(items):
            item.setBackground(bg_brush)
            self.table.setItem(row, i, item)
            
        self.apply_filters() # Re-apply filters to ensure new row visibility is correct

    def clear_filters(self):
        self.combo_type.setCurrentIndex(0)
        self.apply_filters()

    def apply_filters(self):
        """T6.3 — Hide rows that don't match the combobox filter"""
        filter_type = self.combo_type.currentText()
        
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1) # Attack Type column
            if item:
                if filter_type == "All" or filter_type == item.text():
                    self.table.setRowHidden(row, False)
                else:
                    self.table.setRowHidden(row, True)

    def export_to_csv(self):
        """T6.4 — Export CSV"""
        if not self.attack_log:
            QMessageBox.information(self, "Export Empty", "There are no threat logs to export.")
            return
            
        default_name = f"uav_threat_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath, _ = QFileDialog.getSaveFileName(self, "Export Threat Logs", default_name, "CSV Files (*.csv)")
        
        if filepath:
            try:
                # Use built-in csv module to avoid pandas dependency issues on client machine
                with open(filepath, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=self.attack_log[0].keys())
                    writer.writeheader()
                    writer.writerows(self.attack_log)
                
                QMessageBox.information(self, "Export Successful", f"Successfully exported {len(self.attack_log)} records to CSV.")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to save CSV file:\n{str(e)}")
