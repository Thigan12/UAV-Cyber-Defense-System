# PHASE 5: Full UI Rebuild — UAV Cyber-Physical IDS Dashboard
**Based on new design mockups (June 2026)**
**Status: PLANNING → IN PROGRESS**

---

## 🏗️ ARCHITECTURE DECISION
> **Migrating from `customtkinter` → `PyQt5`**
> Reason: The new design requires `QWebEngineView` (Leaflet.js map), `QTableWidget` (Threat Logs), `QDial/QChart` (gauges), and `QTimer` (real-time updates) — none of which are available in customtkinter.
> **The entire `UAVDataBridge` backend class stays 100% unchanged.** Only the UI layer is rebuilt.

---

## ✅ PHASE 4 STATUS (Already Done — Do Not Touch)
- [x] `UAVDataBridge` class — MAVLink loop, 26-feature extraction, 5-class BiLSTM inference
- [x] `FeatureExtractor` — all 26 features wired and tested
- [x] `trigger_mitigation()` — 4 specific defense protocols working
- [x] `send_command()` — Takeoff, RTL, Land, speed/alt control
- [x] Satellite map with flight path drawing
- [x] AI confidence gauge (half-circle)
- [x] Attack history log

---

## ✅ TASK 0 — Project Setup & Dependencies
**Goal:** Install PyQt5 stack and scaffold new file structure.

- [x] **T0.1** Install PyQt5 packages
  ```
  pip install PyQt5 PyQtWebEngine folium reportlab fpdf2
  ```
- [x] **T0.2** Create new file: `dashboard_pyqt.py` (do NOT delete `desktop_app.py` yet)
- [x] **T0.3** Create `ui/` folder for page modules:
  - `ui/page_dashboard.py`
  - `ui/page_telemetry.py`
  - `ui/page_ai_detection.py`
  - `ui/page_live_map.py`
  - `ui/page_threat_logs.py`
  - `ui/page_reports.py`
  - `ui/page_settings.py`
- [x] **T0.4** Create `assets/` folder for icons, map HTML template
- [x] **T0.5** Update `.gitignore` to exclude `__pycache__/`, `*.pyc`

---

## ✅ TASK 1 — Main Window Shell + Sidebar
**File:** `dashboard_pyqt.py`
**Goal:** Build the outer shell — top header bar, left sidebar, right content area.

### T1.1 — Top Header Bar
**Function:** `build_header_bar(self) -> QWidget`
- Fixed height bar at top of window
- Left: UAV IDS logo + "CYBER-PHYSICAL INTRUSION DETECTION SYSTEM" text
- Centre: 6 status pill widgets (CONNECTION, UAV STATUS, ARMED, GPS, BATTERY, TIME)
- Right: Red `EMERGENCY STOP` button
- Each pill updates via `QTimer` every 1 second from `UAVDataBridge` state
- **Data sources:**
  - `bridge.is_connected` → CONNECTION pill
  - `bridge.current_flight_mode` → UAV STATUS pill
  - `bridge.state_dict['armed']` → ARMED pill
  - `bridge.state_dict['lat']` → GPS pill (satellite count)
  - `bridge.state_dict['battery']` → BATTERY pill
  - `datetime.utcnow()` → TIME pill

### T1.2 — Left Sidebar Navigation
**Function:** `build_sidebar(self) -> QWidget`
- Fixed width (200px) vertical panel
- 8 nav buttons: Dashboard, Live Telemetry, AI Detection, Live Map, Threat Logs, Reports, Settings, About
- Active button highlighted with accent colour
- Click → calls `switch_page(page_name: str)`
- Bottom: SITL connection indicator (green dot + `udp:127.0.0.1:14550`)

### T1.3 — Page Switcher
**Function:** `switch_page(self, page_name: str)`
- Uses `QStackedWidget` to show/hide pages
- No page reload — all pages stay alive in memory
- Updates sidebar active button highlight

### T1.4 — PyQt Signal Bridge Adapter
**Class:** `BridgeSignalAdapter(QObject)`
- Wraps `UAVDataBridge` callbacks into proper PyQt signals
- Signals emitted:
  - `telemetry_updated = pyqtSignal(dict)` — emits full telemetry dict at 10Hz
  - `attack_detected = pyqtSignal(int, float)` — emits (attack_class, confidence)
  - `log_message = pyqtSignal(str, str)` — emits (message, log_type)
- All pages connect to these signals — no direct bridge access from pages

---

## ✅ TASK 2 — Dashboard Page (Main Threat View)
**File:** `ui/page_dashboard.py`
**Class:** `DashboardPage(QWidget)`
**Goal:** Replicate the main dashboard exactly as shown in design image.

### T2.1 — UAV Telemetry Live Bar
**Function:** `update_telemetry_bar(self, data: dict)`
- 8 metric cards in a horizontal row below header
- Values: Altitude, Ground Speed, Vertical Speed, Heading, Latitude, Longitude, Satellites, Battery
- Cards use icon + value + unit label
- Updates at 10Hz from `telemetry_updated` signal

### T2.2 — Threat Detected Alert Banner
**Function:** `update_threat_banner(self, attack_class: int, confidence: float)`
- Hidden when `attack_class == 0` (Normal)
- Visible + pulsing red animation when attack detected
- Shows: Attack name, Confidence %, Risk Level (LOW/MEDIUM/CRITICAL)
- Consensus counter: "3 / 3" with progress dots
- **Risk Level logic:**
  - confidence < 0.70 → LOW (yellow)
  - confidence < 0.90 → MEDIUM (orange)
  - confidence ≥ 0.90 → CRITICAL (red)

### T2.3 — Live Map Panel (Left)
**Function:** `build_map_panel(self) -> QWidget`
- `QWebEngineView` loading `assets/map.html` (Leaflet.js with satellite tiles)
- Legend: Home (green), Path (green line), Current Position (red UAV icon)
- JavaScript bridge: Python calls `map.js` functions via `page().runJavaScript()`
- **JS functions called from Python:**
  - `updateDronePosition(lat, lon)` — moves drone marker
  - `addPathPoint(lat, lon)` — appends to flight path polyline
  - `showAttackZone(lat, lon)` — draws red circle at attack point
  - `showRTLPath(lat, lon, home_lat, home_lon)` — draws dashed red line

### T2.4 — Live Telemetry Graphs Panel (Right)
**Function:** `build_graphs_panel(self) -> QWidget`
- 5 stacked Matplotlib graphs in `FigureCanvas` (PyQt5)
- Graphs shown (last 60 seconds on X axis):
  1. Altitude (m) — yellow line
  2. Ground Speed (m/s) — blue line
  3. GPS Jump Magnitude (m) — red line (from `gps_jump_magnitude` feature)
  4. RC Channel 1 Raw — orange line (from `chan1_raw`)
  5. Servo Output 1 (PWM) — purple line (from `servo1_raw`)
- **Data sources:** all already in `state_dict` inside `UAVDataBridge`
- Scrolling X-axis, auto-scaling Y-axis
- Redraws at 1Hz to save CPU

### T2.5 — AI Prediction Panel (Right sidebar)
**Function:** `build_ai_panel(self) -> QWidget`
- Current prediction label (class name in colour)
- Full circular confidence gauge (QDial or custom `QPainter` arc)
- Prediction history dots — last 20 predictions shown as coloured dots
  - Each dot colour = class colour (green=Normal, red=RC Hijack, orange=Mode Forcing, etc.)
- Class legend: 0–4 with colour dots and names

### T2.6 — Zero-Trust Mitigation Checklist
**Function:** `update_mitigation_checklist(self, step: int)`
- 6-row checklist widget (icon + label + status badge)
- Steps: Anomaly Detected → Consensus Reached → Communication Severed → RTL Command Sent → Returning to Launch → Safe Landing
- Each step lights up DONE (green) / IN PROGRESS (blue) / PENDING (grey)
- Driven by `attack_detected` signal — steps tick off automatically with 1s delay between each

### T2.7 — Attack Logs Table (Bottom)
**Function:** `build_attack_log_table(self) -> QTableWidget`
- 6 columns: Time, Attack Type, Confidence, Altitude, Location, Action Taken, Status
- New row added on each confirmed attack
- Attack Type cell coloured by type
- Status: "In Progress" (orange) → "Completed" (green) after mitigation

### T2.8 — Control Panel (Bottom Right)
**Function:** `build_control_panel(self) -> QWidget`
- 6 buttons: Start Monitoring, Stop Monitoring, Manual RTL, Export Report, Clear Logs, Settings
- Start/Stop Monitoring toggles `UAVDataBridge` thread (or just suppresses alerts)
- Manual RTL → calls `bridge.send_command('RTL')`
- Export Report → opens Reports page
- System Status label at bottom: "All Systems Operational" (green) or "THREAT ACTIVE" (red)

---

## ✅ TASK 3 — Live Telemetry Page
**File:** `ui/page_telemetry.py`
**Class:** `TelemetryPage(QWidget)`
**Goal:** Show all raw MAVLink values in real-time with graphs.

### T3.1 — Top Metric Cards Row
**Function:** `update_top_metrics(self, data: dict)`
- 6 cards: Altitude, Ground Speed, Climb Rate, Heading, Battery, GPS Satellites
- Large font value + unit + icon
- Data from `VFR_HUD` and `GPS_RAW_INT` messages

### T3.2 — 3 Live Scrolling Graphs
**Function:** `build_telemetry_graphs(self) -> QWidget`
- Graph 1: Altitude (m) — last 60s
- Graph 2: Ground Speed (m/s) — last 60s
- Graph 3: Climb Rate (m/s) — last 60s
- All using Matplotlib `FigureCanvas` in PyQt5
- Redraws at 1Hz

### T3.3 — Bottom Metric Cards Row
**Function:** `update_bottom_metrics(self, data: dict)`
- 7 cards: Latitude, Longitude, RTL Distance, Air Speed, Throttle, Flight Mode, Armed State
- **RTL Distance calculation:**
  ```python
  def calc_rtl_distance(lat, lon, home_lat, home_lon) -> float:
      # Haversine formula → returns distance in km
  ```
- Flight Mode uses mode_names dict (same as current code)
- Armed State: "ARMED" (green) / "DISARMED" (red)

---

## ✅ TASK 4 — AI Detection Page
**File:** `ui/page_ai_detection.py`
**Class:** `AIDetectionPage(QWidget)`

### T4.1 — Current Prediction Display
**Function:** `update_prediction(self, pred_class: int, confidence: float)`
- Large class name label with colour coding
- "ATTACK DETECTED" badge (red) or "NORMAL FLIGHT" badge (green)

### T4.2 — Full Circular Confidence Gauge
**Function:** `draw_confidence_gauge(self, value: float)`
- Custom `QPainter` arc drawing (full circle, not half)
- Colour changes: green → yellow → orange → red based on value
- Centre text: percentage value

### T4.3 — 3-Tick Consensus Display
**Function:** `update_consensus(self, tick_count: int)`
- 3 circle icons — fill green as ticks accumulate
- "CONSENSUS REACHED" text appears when tick_count == 3
- **Backend change needed in `UAVDataBridge`:**
  - Add `self.consensus_counter = 0` to `__init__`
  - In inference loop: if `pred_class == last_pred_class`: `consensus_counter += 1` else reset to 0
  - Emit consensus count via callback

### T4.4 — Attack Class Probability Bars
**Function:** `update_class_bars(self, pred_array: np.ndarray)`
- 5 horizontal progress bars (one per class)
- Labels: 0 Normal, 1 RC Hijack, 2 Mode Forcing, 3 GPS Spoofing, 4 Disarm
- Each bar width = class probability %
- Colour coded per class

### T4.5 — Confidence Over Time Graph
**Function:** `update_confidence_graph(self, confidence: float)`
- Line graph, last 60 seconds
- Y-axis: 0–100%
- Matplotlib `FigureCanvas`

### T4.6 — Feature Importance Bar Chart
**Function:** `build_feature_importance_chart(self) -> QWidget`
- **Static chart** — top 8 most important features from your 26
- Based on known importance from training (hardcoded or from SHAP)
- Top features (based on your model design):
  1. `rc_chan1_raw` — RC Hijack signature
  2. `gps_jump_magnitude` — GPS Spoofing signature
  3. `alt_delta` — Mode Forcing signature
  4. `servo1_raw` — Disarm signature
  5. `rollspeed` — Attitude anomaly
  6. `armed_state` — Disarm detection
  7. `alt_trend` — Altitude deviation
  8. `vz` — Vertical velocity
- Horizontal bar chart using Matplotlib

### T4.7 — Recent Predictions Table
**Function:** `add_prediction_row(self, pred_class: int, confidence: float, consensus: int)`
- Rolling table, last 10 predictions
- Columns: Time (UTC), Prediction, Confidence, Consensus, Action
- Action = "RTL Activated" / "Monitoring" / "None"

---

## ✅ TASK 5 — Live Map Page
**File:** `ui/page_live_map.py`
**Class:** `LiveMapPage(QWidget)`

### T5.1 — Leaflet.js Map HTML Template
**File:** `assets/map.html`
- Satellite tile layer (Google or Esri)
- Drone marker with custom red icon
- Home marker (green H icon)
- Flight path polyline (green, updates dynamically)
- RTL path (dashed red line)
- Attack zone (red filled circle, 50m radius)
- All markers/paths updated via `QWebChannel` or `runJavaScript()`

### T5.2 — QWebEngineView Integration
**Function:** `build_map_view(self) -> QWebEngineView`
- Load `map.html` from local file
- Set up `QWebChannel` for bidirectional Python↔JS communication
- **Python → JS calls:**
  - `updateDronePosition(lat, lon, alt, speed)` — moves marker + updates popup
  - `addPathPoint(lat, lon)` — extends polyline
  - `setHomePosition(lat, lon)` — places home marker
  - `showAttackZone(lat, lon)` — red circle at attack location
  - `clearAttackZone()` — removes red circle
  - `showRTLPath(from_lat, from_lon, to_lat, to_lon)` — dashed RTL line

### T5.3 — Map Info Panel
**Function:** `update_map_info(self, data: dict)`
- Right side panel, 6 static fields updated at 1Hz:
  - Current Lat, Current Lon, Altitude, Ground Speed, RTL Distance, Satellites

### T5.4 — Map Control Buttons
**Function:** `build_map_controls(self) -> QWidget`
- Zoom In → `runJavaScript("map.zoomIn()")`
- Zoom Out → `runJavaScript("map.zoomOut()")`
- Center UAV → `runJavaScript(f"map.setView([{lat}, {lon}], 18)")`
- Show RTL Path toggle → calls `showRTLPath()` or `clearRTLPath()`

---

## ✅ TASK 6 — Threat Logs Page
**File:** `ui/page_threat_logs.py`
**Class:** `ThreatLogsPage(QWidget)`

### T6.1 — Attack Log Data Store
**In `UAVDataBridge`:** Add `self.attack_log = []` list
- Each confirmed attack appends a dict:
  ```python
  {
    "time": "2026-05-26 14:35:40",
    "attack_type": "RC Hijack",
    "confidence": 96.7,
    "lat": 34.052184,
    "lon": -118.243702,
    "altitude": 86.7,
    "action": "RTL Activated",
    "status": "Mitigated"
  }
  ```

### T6.2 — Threat Log Table
**Function:** `build_log_table(self) -> QTableWidget`
- 7 columns: Time, Attack Type, Confidence, Location, Altitude (m), Action Taken, Status
- Row background colour by attack type:
  - RC Hijack → red tint (`#3d0000`)
  - Mode Forcing → orange tint (`#3d1a00`)
  - GPS Spoofing → yellow tint (`#2d2d00`)
  - Normal → green tint (`#002d00`)
- Status badge: "Mitigated" (red), "Blocked" (orange), "Safe" (green)

### T6.3 — Filter Controls
**Function:** `apply_filters(self)`
- Attack type filter: `QComboBox` (All / RC Hijack / GPS Spoofing / Mode Forcing / Disarm / Normal)
- Date filter: `QDateEdit`
- Filters update table in real-time using `QSortFilterProxyModel`

### T6.4 — Export CSV
**Function:** `export_to_csv(self)`
- Uses `pandas.DataFrame(self.attack_log).to_csv(filepath)`
- Opens `QFileDialog` to pick save location
- Shows success notification

---

## ✅ TASK 7 — Reports Page
**File:** `ui/page_reports.py`
**Class:** `ReportsPage(QWidget)`

### T7.1 — Report Type Selector
**Function:** `on_report_type_selected(self, report_type: str)`
- 4 radio buttons: Incident Report, Daily Summary, Model Performance, System Health
- Selection updates the "Include in Report" checkboxes dynamically

### T7.2 — Include In Report Checkboxes
- 5 checkboxes: Telemetry Summary, Prediction Graphs, Map & Flight Path, Threat Timeline, System Information

### T7.3 — Graph Capture for PDF
**Function:** `capture_graphs_as_images(self) -> list[str]`
- Saves current Matplotlib figures to temp PNG files using `fig.savefig()`
- Returns list of image file paths for embedding in PDF

### T7.4 — PDF Generator
**Function:** `generate_pdf(self, report_type: str, sections: list) -> str`
- Uses `reportlab` or `fpdf2`
- Cover page: UAV IDS logo, report title, date/time, flight session info
- Sections included based on checkbox selections:
  - Telemetry Summary → table of min/max/avg values
  - Prediction Graphs → embedded PNG from `capture_graphs_as_images()`
  - Threat Timeline → attack log table
  - System Information → model name, version, thresholds
- Returns path to saved PDF

### T7.5 — Preview Panel
**Function:** `show_preview(self, pdf_path: str)`
- Uses `QWebEngineView` to render HTML preview
- Or `QTextBrowser` for basic rich-text preview

### T7.6 — Export PDF Button
**Function:** `on_export_pdf(self)`
- Calls `generate_pdf()` → opens `QFileDialog` → saves PDF
- Shows "PDF Exported Successfully" notification

---

## ✅ TASK 8 — Settings Page
**File:** `ui/page_settings.py`
**Class:** `SettingsPage(QWidget)`

### T8.1 — Connection Settings
- MAVLink URL input (default: `udp:127.0.0.1:14550`)
- Reconnect button → restarts `UAVDataBridge` thread

### T8.2 — AI Model Settings
- Model file path selector (`QFileDialog`)
- Scaler file path selector
- Confidence threshold slider (default: 0.95)
- Warmup time slider (default: 90s)
- Consensus ticks required (default: 3)

### T8.3 — Save Settings
**Function:** `save_settings(self)`
- Saves to `config.json`
- Reloads bridge with new parameters

---

## ✅ TASK 9 — Backend Bridge Upgrades
**File:** `desktop_app.py` (existing `UAVDataBridge`)
**Goal:** Small additions to support new UI — no breaking changes.

### T9.1 — 3-Tick Consensus Counter
```python
# Add to __init__:
self.consensus_counter = 0
self.last_pred_class = 0

# Add to inference loop (after pred_class is determined):
if pred_class == self.last_pred_class and pred_class != 0:
    self.consensus_counter = min(self.consensus_counter + 1, 3)
else:
    self.consensus_counter = 0
self.last_pred_class = pred_class
```

### T9.2 — Full pred_array Emission
- Currently only emits `(lat, lon, alt, spd, is_attack, confidence, attack_type)`
- New: also emit `pred_array` (all 5 class probabilities) for AI Detection page bars

### T9.3 — Attack Log Storage
- Add `self.attack_log = []` list
- Append structured dict on each confirmed attack (see T6.1)

### T9.4 — Battery Data
- Currently not parsed — add `SYS_STATUS` to `TARGET_MESSAGES`
- Parse `msg.battery_remaining` → expose as `bridge.battery_pct`

### T9.5 — Satellite Count
- Add parsing of `GPS_RAW_INT.satellites_visible` → `bridge.gps_satellites`

---

## ✅ TASK 10 — Theming & Polish
**File:** `ui/theme.py`
**Goal:** Consistent dark military theme across all pages using QSS.

### T10.1 — Global QSS Stylesheet
```python
# Colour tokens:
BG_DARK = "#0a0f18"
PANEL_BG = "#131b26"
ACCENT_CYAN = "#00d4ff"
ACCENT_PURPLE = "#7c3aed"
SAFE_GREEN = "#00ff88"
ALERT_RED = "#ff003c"
WARN_ORANGE = "#ff6600"
TEXT_PRIMARY = "#e2e8f0"
TEXT_MUTED = "#64748b"
```

---

## 📁 Expected File Structure

```
FYP PROJECT/
├── dashboard_pyqt.py          ← NEW main entry point (PyQt5)
├── desktop_app.py             ← OLD (keep until new is stable)
├── feature_extractor.py       ← UNCHANGED
├── train_models.py            ← UNCHANGED
├── log_telemetry.py           ← UNCHANGED
├── simulate_attack.py         ← UNCHANGED
├── auto_generate_dataset.py   ← UNCHANGED
├── config.json                ← NEW settings file
├── ui/
│   ├── __init__.py
│   ├── page_dashboard.py
│   ├── page_telemetry.py
│   ├── page_ai_detection.py
│   ├── page_live_map.py
│   ├── page_threat_logs.py
│   ├── page_reports.py
│   ├── page_settings.py
│   └── theme.py
├── assets/
│   ├── map.html               ← Leaflet.js map template
│   ├── drone_icon.png
│   └── logo.png
├── PHASE5_UI_REBUILD_TASKS.md ← THIS FILE
├── MASTER_TASK_JOURNEY.md
├── README.md
└── .gitignore
```
