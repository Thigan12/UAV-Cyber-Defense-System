import os
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QFrame, QRadioButton, QCheckBox, QPushButton, 
                             QTextBrowser, QFileDialog, QMessageBox, QGridLayout)
from PyQt5.QtCore import Qt
from fpdf import FPDF # Uses fpdf2

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

class ReportsPage(QWidget):
    """Reports — report type selector, preview, PDF export."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        lbl = QLabel("INCIDENT REPORT EXPORT MODULE")
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 800; letter-spacing: 2px;")
        header_layout.addWidget(lbl)
        header_layout.addStretch()
        
        self.btn_export = QPushButton("GENERATE PDF REPORT")
        self.btn_export.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_CYAN}; color: {BG_DARK}; 
                padding: 10px 20px; border-radius: 5px; 
                font-weight: bold; font-size: 13px; letter-spacing: 1px;
            }}
            QPushButton:hover {{ background-color: #00b8d9; }}
        """)
        self.btn_export.clicked.connect(self.on_export_pdf)
        header_layout.addWidget(self.btn_export)
        
        self.main_layout.addLayout(header_layout)
        
        self.main_split = QHBoxLayout()
        self.main_layout.addLayout(self.main_split, stretch=1)
        
        # Left Panel: Settings
        self.left_panel = QVBoxLayout()
        self.left_panel.setSpacing(20)
        self.main_split.addLayout(self.left_panel, stretch=1)
        
        self.build_type_selector()
        self.build_checkboxes()
        self.left_panel.addStretch()
        
        # Right Panel: Preview
        self.right_panel = QVBoxLayout()
        self.main_split.addLayout(self.right_panel, stretch=2)
        self.build_preview_panel()
        
        # Initialize preview
        self.update_preview()

    def build_type_selector(self):
        panel = CardPanel("DOCUMENT CLASSIFICATION", ACCENT_CYAN)
        
        self.report_types = [
            ("Incident Report", "Detailed breakdown of a specific cyber-attack event."),
            ("Daily Summary", "Aggregated telemetry and security events over 24 hours."),
            ("Model Performance", "AI confidence and false-positive metrics."),
            ("System Health", "Hardware integrity, battery, and MAVLink link stability.")
        ]
        self.radio_buttons = []
        
        for i, (rtype, desc) in enumerate(self.report_types):
            rb = QRadioButton(rtype)
            rb.setStyleSheet(f"""
                QRadioButton {{ color: {TEXT_PRIMARY}; font-weight: bold; font-size: 13px; border: none; }}
                QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 7px; border: 2px solid {BORDER_DEFAULT}; }}
                QRadioButton::indicator:checked {{ background-color: {ACCENT_CYAN}; border: 2px solid {ACCENT_CYAN}; }}
            """)
            if i == 0: rb.setChecked(True)
            rb.toggled.connect(self.on_report_type_selected)
            self.radio_buttons.append(rb)
            
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; margin-left: 20px; margin-bottom: 5px; border: none;")
            
            panel.layout.addWidget(rb)
            panel.layout.addWidget(desc_lbl)
            
        self.left_panel.addWidget(panel)

    def build_checkboxes(self):
        panel = CardPanel("DATA INCLUSION PARAMETERS", ACCENT_PURPLE)
        
        sections = [
            ("Telemetry Summary", "Include average speed, altitude, and mode changes."),
            ("Prediction Graphs", "Export Matplotlib AI probability trend graphs."),
            ("Map & Flight Path", "Export Leaflet map trajectory and threat zones."),
            ("Threat Timeline", "Tabular log of detected anomalies and mitigations."),
            ("System Information", "Include battery, GPS satellites, and connection status.")
        ]
        self.checkboxes = {}
        
        for sec, desc in sections:
            cb = QCheckBox(sec)
            cb.setStyleSheet(f"""
                QCheckBox {{ color: {TEXT_PRIMARY}; font-weight: bold; font-size: 13px; border: none; }}
                QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 3px; border: 2px solid {BORDER_DEFAULT}; }}
                QCheckBox::indicator:checked {{ background-color: {ACCENT_PURPLE}; border: 2px solid {ACCENT_PURPLE}; image: url(check.png); }}
            """)
            cb.setChecked(True)
            cb.stateChanged.connect(self.update_preview)
            self.checkboxes[sec] = cb
            
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; margin-left: 24px; margin-bottom: 5px; border: none;")
            
            panel.layout.addWidget(cb)
            panel.layout.addWidget(desc_lbl)
            
        self.left_panel.addWidget(panel)

    def build_preview_panel(self):
        panel = CardPanel("DOCUMENT PREVIEW ENGINE", TEXT_MUTED)
        
        self.preview_browser = QTextBrowser()
        self.preview_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: #ffffff; 
                color: #000000; 
                border: 1px solid {BORDER_DEFAULT}; 
                border-radius: 4px;
                padding: 30px; 
                font-family: serif;
            }}
        """)
        panel.layout.addWidget(self.preview_browser)
        
        self.right_panel.addWidget(panel)

    def set_data(self, attack_log=None, system_info=None):
        self.attack_log = attack_log or []
        self.system_info = system_info or {}
        self.update_preview()

    def on_report_type_selected(self):
        """T7.1 — Auto-check relevant boxes based on type"""
        selected_type = self.report_types[0] # Safe default
        for rb in self.radio_buttons:
            if rb.isChecked():
                selected_type = rb.text()
                break
                
        if selected_type == "Incident Report":
            self.checkboxes["Threat Timeline"].setChecked(True)
            self.checkboxes["Map & Flight Path"].setChecked(True)
        elif selected_type == "System Health":
            self.checkboxes["System Information"].setChecked(True)
            self.checkboxes["Telemetry Summary"].setChecked(True)
            
        self.update_preview()

    def update_preview(self):
        """T7.5 — Preview Panel updating"""
        selected_type = self.report_types[0] # Safe default
        for rb in self.radio_buttons:
            if rb.isChecked():
                selected_type = rb.text()
                break
                
        html = f"""
        <h1 style='color: #800000; text-align: center;'>UAV CYBER-PHYSICAL IDS</h1>
        <h2 style='text-align: center;'>{selected_type}</h2>
        <p style='text-align: center;'>Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
        <hr>
        """
        
        for name, cb in self.checkboxes.items():
            if cb.isChecked():
                html += f"<h3>{name}</h3>"
                
                if name == "System Information":
                    batt = getattr(self, 'system_info', {}).get('battery', 'N/A')
                    sats = getattr(self, 'system_info', {}).get('satellites', 'N/A')
                    fmode = getattr(self, 'system_info', {}).get('flight_mode', '0')
                    html += f"<ul><li><b>Battery Level:</b> {batt}%</li>"
                    html += f"<li><b>GPS Satellites:</b> {sats}</li>"
                    html += f"<li><b>Last Flight Mode ID:</b> {fmode}</li></ul>"
                    
                elif name == "Threat Timeline":
                    logs = getattr(self, 'attack_log', [])
                    if not logs:
                        html += "<p><i>No cyber-threats detected during this session.</i></p>"
                    else:
                        html += "<table border='1' cellspacing='0' cellpadding='5' width='100%'>"
                        html += "<tr style='background-color:#eee;'><th>Time (UTC)</th><th>Attack Type</th><th>Confidence</th><th>Mitigation Action</th></tr>"
                        for log in logs:
                            html += f"<tr><td>{log.get('time')}</td><td>{CLASS_NAMES.get(log.get('attack_type',0), 'Unknown')}</td>"
                            html += f"<td>{log.get('confidence')}%</td><td>{log.get('action')}</td></tr>"
                        html += "</table>"
                else:
                    html += f"<p>[Detailed {name} data included in final PDF]</p>"
                
        html += "<hr><p style='font-size: 10px; text-align: center;'>Autogenerated by Zero-Trust Intrusion Detection System</p>"
        self.preview_browser.setHtml(html)

    def capture_graphs_as_images(self) -> list:
        """T7.3 — Graph Capture for PDF (Mocked for UI logic)"""
        # In a fully integrated system, this would iterate through other pages,
        # get the Matplotlib Figures, and call .savefig(path).
        return []

    def generate_pdf(self, filepath: str):
        """T7.4 — PDF Generator using fpdf2"""
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font("helvetica", "B", 24)
        pdf.set_text_color(128, 0, 0) # Dark red
        pdf.cell(0, 15, "UAV CYBER-PHYSICAL IDS", new_x="LMARGIN", new_y="NEXT", align="C")
        
        selected_type = self.report_types[0] # Safe default
        for rb in self.radio_buttons:
            if rb.isChecked():
                selected_type = rb.text()
                break

        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, selected_type, new_x="LMARGIN", new_y="NEXT", align="C")
        
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 10, f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)
        
        # Sections
        pdf.set_text_color(0, 0, 0)
        for name, cb in self.checkboxes.items():
            if cb.isChecked():
                pdf.set_font("helvetica", "B", 14)
                pdf.cell(0, 10, name, new_x="LMARGIN", new_y="NEXT", border="B")
                pdf.ln(2)
                
                pdf.set_font("helvetica", "", 11)
                if name == "System Information":
                    batt = getattr(self, 'system_info', {}).get('battery', 'N/A')
                    sats = getattr(self, 'system_info', {}).get('satellites', 'N/A')
                    fmode = getattr(self, 'system_info', {}).get('flight_mode', '0')
                    pdf.cell(0, 8, f"Battery Level: {batt}%", new_x="LMARGIN", new_y="NEXT")
                    pdf.cell(0, 8, f"GPS Satellites: {sats}", new_x="LMARGIN", new_y="NEXT")
                    pdf.cell(0, 8, f"Last Flight Mode ID: {fmode}", new_x="LMARGIN", new_y="NEXT")
                    
                elif name == "Threat Timeline":
                    logs = getattr(self, 'attack_log', [])
                    if not logs:
                        pdf.set_font("helvetica", "I", 11)
                        pdf.cell(0, 8, "No cyber-threats detected during this session.", new_x="LMARGIN", new_y="NEXT")
                    else:
                        # Table Header
                        pdf.set_font("helvetica", "B", 10)
                        col_w = [40, 40, 25, 80]
                        pdf.cell(col_w[0], 8, "Time (UTC)", border=1)
                        pdf.cell(col_w[1], 8, "Attack Type", border=1)
                        pdf.cell(col_w[2], 8, "Confidence", border=1)
                        pdf.cell(col_w[3], 8, "Mitigation Action", border=1, new_x="LMARGIN", new_y="NEXT")
                        
                        # Table Rows
                        pdf.set_font("helvetica", "", 10)
                        for log in logs:
                            t_type = CLASS_NAMES.get(log.get('attack_type',0), 'Unknown')
                            t_conf = f"{log.get('confidence')}%"
                            t_act = log.get('action', 'N/A')
                            pdf.cell(col_w[0], 8, str(log.get('time')), border=1)
                            pdf.cell(col_w[1], 8, str(t_type), border=1)
                            pdf.cell(col_w[2], 8, str(t_conf), border=1)
                            pdf.cell(col_w[3], 8, str(t_act), border=1, new_x="LMARGIN", new_y="NEXT")
                else:
                    pdf.set_font("helvetica", "I", 10)
                    pdf.multi_cell(0, 8, f"Detailed logs for {name} will be attached in future system updates. Refer to raw logs for deep analysis.")
                
                pdf.ln(5)
                
        # Footer
        pdf.set_y(-25)
        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 10, "Autogenerated by Zero-Trust Intrusion Detection System", align="C")
        
        pdf.output(filepath)

    def on_export_pdf(self):
        """T7.6 — Export PDF Button"""
        default_name = f"UAV_Report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(self, "Export PDF Report", default_name, "PDF Files (*.pdf)")
        
        if filepath:
            try:
                self.generate_pdf(filepath)
                QMessageBox.information(self, "Export Successful", f"Report successfully saved to:\n{filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to generate PDF:\n{str(e)}")
