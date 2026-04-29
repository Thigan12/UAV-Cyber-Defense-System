import time
import queue
import pickle
import threading
import collections
import numpy as np
import tensorflow as tf
from pymavlink import mavutil
import customtkinter as ctk
import tkintermapview
import tkinter as tk
from PIL import Image, ImageTk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- CYBERPUNK / MILITARY THEME ---
BG_DARK = "#0a0f18"
PANEL_BG = "#131b26"
NEON_CYAN = "#00f0ff"
NEON_RED = "#ff003c"
SAFE_GREEN = "#00ff66"
TEXT_COLOR = "#e2e8f0"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class UAVDataBridge:
    """ Handles MAVLink communication and LSTM inference securely in the background """
    def __init__(self, ui_callback):
        self.ui_callback = ui_callback
        self.vehicle = None
        self.is_compromised = False
        
        # LSTM Model
        self.model = tf.keras.models.load_model('lstm_uav_model.h5')
        with open('scaler.pkl', 'rb') as f:
            self.scaler = pickle.load(f)
            
        self.TIME_STEPS = 10
        self.rolling_window = collections.deque(maxlen=self.TIME_STEPS)
        self.current_state = np.zeros(19)
        self.home_alt = None
        self.target_alt = 10
        self.target_speed = 5
        
        # Thread
        self.thread = threading.Thread(target=self._loop)
        self.thread.daemon = True
        self.thread.start()

    def _loop(self):
        self.ui_callback(msg_log="Connecting to SITL on udp:127.0.0.1:14550...", log_type="system")
        self.vehicle = mavutil.mavlink_connection('udp:127.0.0.1:14550')
        self.vehicle.wait_heartbeat()
        self.ui_callback(msg_log="Heartbeat received! Link established.", log_type="system")
        
        self.vehicle.mav.request_data_stream_send(
            self.vehicle.target_system, self.vehicle.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_ALL, 10, 1
        )
        
        TARGET_MESSAGES = ['GPS_RAW_INT', 'ATTITUDE', 'VFR_HUD', 'HEARTBEAT']
        self.vfr_alt = 0.0
        
        while True:
            msg = self.vehicle.recv_match(type=TARGET_MESSAGES, blocking=True, timeout=1.0)
            if not msg: continue
            
            msg_type = msg.get_type()
            
            # Send raw text to UI Terminal
            self.ui_callback(msg_log=f"{msg_type} {msg}", log_type="packet")
            
            if msg_type == 'GPS_RAW_INT':
                self.current_state[0:8] = [msg.lat, msg.lon, msg.alt, msg.eph, msg.epv, msg.vel, msg.cog, msg.satellites_visible]
            elif msg_type == 'ATTITUDE':
                self.current_state[8:14] = [msg.roll, msg.pitch, msg.yaw, msg.rollspeed, msg.pitchspeed, msg.yawspeed]
            elif msg_type == 'VFR_HUD':
                self.current_state[14:19] = [msg.airspeed, msg.groundspeed, msg.heading, msg.throttle, msg.climb]
                self.vfr_alt = msg.alt # VFR_HUD provides highly smooth EKF altitude in meters!
                
            self.rolling_window.append(self.current_state.copy())
            
            is_attack = False
            confidence = 0.0
            if len(self.rolling_window) == self.TIME_STEPS:
                window_scaled = self.scaler.transform(np.array(self.rolling_window))
                window_reshaped = np.reshape(window_scaled, (1, self.TIME_STEPS, 19))
                pred = self.model.predict(window_reshaped, verbose=0)[0][0]
                
                # --- AI NOISE GATE & SMOOTHING ---
                # 1. Noise Floor: Suppress background uncertainty if drone is idling
                if pred < 0.5:
                    raw_conf = float(pred) * 0.1
                else:
                    raw_conf = float(pred)
                
                # 2. Rolling Average (last 5 predictions) to stop UI jitter
                if not hasattr(self, 'conf_history'):
                    self.conf_history = collections.deque(maxlen=5)
                self.conf_history.append(raw_conf)
                
                confidence = float(sum(self.conf_history) / len(self.conf_history))
                
                # 3. Trigger red alert only if smoothed confidence breaks 55%
                is_attack = bool(confidence > 0.55)
                
            # Emit telemetry to UI
            lat = float(self.current_state[0]) / 1e7 if self.current_state[0] != 0 else 0
            lon = float(self.current_state[1]) / 1e7 if self.current_state[1] != 0 else 0
            
            # Use VFR_HUD smoothed altitude for the Graph, not raw GPS
            if self.home_alt is None and self.vfr_alt != 0:
                self.home_alt = self.vfr_alt
                
            alt = self.vfr_alt
            if self.home_alt is not None:
                alt = max(0.0, self.vfr_alt - self.home_alt)
                
            spd = float(self.current_state[14])
            
            self.ui_callback(telemetry=(lat, lon, alt, spd, is_attack, confidence))

    def trigger_mitigation(self):
        if self.is_compromised or not self.vehicle: return
        self.is_compromised = True
        def _mitigate():
            self.ui_callback(msg_log="⚠ UNAUTHORIZED MAVLINK INJECTION SUSPECTED", log_type="alert")
            time.sleep(0.5)
            self.ui_callback(msg_log="[SYSTEM] INITIATING ZERO-TRUST PROTOCOL...", log_type="alert")
            time.sleep(0.5)
            
            self.ui_callback(msg_log="[SYSTEM] Disabling external RC Overrides...", log_type="alert")
            self.vehicle.mav.param_set_send(
                self.vehicle.target_system, self.vehicle.target_component,
                b'RC_OVERRIDE_TIME', 0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32
            )
            time.sleep(0.5)
            
            self.ui_callback(msg_log="[SYSTEM] Locking manual flight controls...", log_type="alert")
            time.sleep(0.5)
            
            self.ui_callback(msg_log="[SYSTEM] Forcing Autonomous Return to Launch (RTL) mode.", log_type="alert")
            self.vehicle.mav.command_long_send(
                self.vehicle.target_system, self.vehicle.target_component,
                mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 6, 0, 0, 0, 0, 0
            )
            time.sleep(0.5)
            self.ui_callback(msg_log="[SYSTEM] Evading threat zone. Returning to Base...", log_type="alert")
        
        threading.Thread(target=_mitigate, daemon=True).start()

    def send_command(self, action):
        if not self.vehicle or self.is_compromised: return
        
        if action == 'TAKEOFF':
            def _takeoff():
                self.ui_callback(msg_log=f"[COMMAND] ARM & TAKEOFF Sequence Initiated...", log_type="system")
                # 1. Set to GUIDED
                self.vehicle.mav.command_long_send(self.vehicle.target_system, self.vehicle.target_component, mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 4, 0, 0, 0, 0, 0)
                self.ui_callback(msg_log=f"[SYSTEM] Mode: GUIDED. Pre-Flight Checks...", log_type="system")
                time.sleep(1.0)
                # 2. Arm
                self.vehicle.mav.command_long_send(self.vehicle.target_system, self.vehicle.target_component, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)
                self.ui_callback(msg_log=f"[SYSTEM] Engaging Engines. Motors Armed.", log_type="system")
                time.sleep(2.0) # MUST wait for motors to fully spool up!
                # 3. Takeoff
                self.vehicle.mav.command_long_send(self.vehicle.target_system, self.vehicle.target_component, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, float(self.target_alt))
                self.ui_callback(msg_log=f"[SYSTEM] Thrust Applied. Target Altitude set to {self.target_alt}m.", log_type="system")
                time.sleep(0.5)
                self.ui_callback(msg_log=f"[SYSTEM] Climbing...", log_type="system")
                
                # Check altitude until safe
                success = False
                for _ in range(20):
                    if self.vfr_alt - self.home_alt >= (self.target_alt - 1.0):
                        success = True
                        break
                    time.sleep(1.0)
                    
                if success:
                    self.ui_callback(msg_log=f"[SYSTEM] Safe Altitude Reached. Hovering in place.", log_type="system")
                else:
                    self.ui_callback(msg_log=f"[SYSTEM] WARNING: Takeoff may have been rejected by autopilot.", log_type="system")
                
            threading.Thread(target=_takeoff, daemon=True).start()
            
        elif action == 'RTL':
            def _rtl():
                self.ui_callback(msg_log=f"[COMMAND] RETURN TO LAUNCH (RTL) INITIATED...", log_type="system")
                time.sleep(0.5)
                self.vehicle.mav.command_long_send(self.vehicle.target_system, self.vehicle.target_component, mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 6, 0, 0, 0, 0, 0)
                self.ui_callback(msg_log=f"[SYSTEM] Flight Mode Override: RTL", log_type="system")
                time.sleep(1.0)
                self.ui_callback(msg_log=f"[SYSTEM] Adjusting altitude for safe return...", log_type="system")
                time.sleep(1.0)
                self.ui_callback(msg_log=f"[SYSTEM] Navigating back to Home coordinate...", log_type="system")
            threading.Thread(target=_rtl, daemon=True).start()
            
        elif action == 'LAND':
            def _land():
                self.ui_callback(msg_log=f"[COMMAND] EMERGENCY LAND OVERRIDE INITIATED!", log_type="system")
                time.sleep(0.5)
                self.vehicle.mav.command_long_send(self.vehicle.target_system, self.vehicle.target_component, mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 9, 0, 0, 0, 0, 0)
                self.ui_callback(msg_log=f"[SYSTEM] Forcing Flight Mode: LAND", log_type="system")
                time.sleep(0.5)
                self.ui_callback(msg_log=f"[SYSTEM] Cutting horizontal speed...", log_type="system")
                time.sleep(0.5)
                self.ui_callback(msg_log=f"[SYSTEM] Decreasing altitude...", log_type="system")
                
                # Wait until grounded
                for _ in range(30):
                    alt_check = float(self.current_state[2]) / 1000.0
                    if self.home_alt is not None: alt_check = max(0.0, alt_check - self.home_alt)
                    if alt_check < 0.5: break
                    time.sleep(1.0)
                self.ui_callback(msg_log=f"[SYSTEM] Touchdown confirmed (0.0m). Motors Disarmed.", log_type="system")
            threading.Thread(target=_land, daemon=True).start()

    def change_speed(self, delta):
        if not self.vehicle or self.is_compromised: return
        self.target_speed = max(1, self.target_speed + delta)
        self.ui_callback(msg_log=f"[COMMAND] Target Speed adjusted to {self.target_speed} m/s", log_type="system")
        self.vehicle.mav.command_long_send(
            self.vehicle.target_system, self.vehicle.target_component,
            mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, 0,
            1, self.target_speed, -1, 0, 0, 0, 0
        )
        
    def change_alt(self, delta):
        if not self.vehicle or self.is_compromised: return
        self.target_alt = max(2, self.target_alt + delta)
        self.ui_callback(msg_log=f"[COMMAND] Target Altitude adjusted to {self.target_alt} m", log_type="system")
        self.vehicle.mav.command_long_send(
            self.vehicle.target_system, self.vehicle.target_component,
            mavutil.mavlink.MAV_CMD_DO_CHANGE_ALTITUDE, 0,
            self.target_alt, 0, 0, 0, 0, 0, 0
        )

    def fly_to_waypoint(self, lat, lon):
        if not self.vehicle or self.is_compromised: return
        
        def _fly():
            self.ui_callback(msg_log=f"[COMMAND] Target Coordinates Received: {lat:.5f}, {lon:.5f}", log_type="system")
            time.sleep(0.5)
            self.ui_callback(msg_log=f"[SYSTEM] Calculating optimal vector path...", log_type="system")
            
            current_alt = float(self.current_state[2]) / 1000.0
            if self.home_alt is not None:
                current_alt = max(0.0, current_alt - self.home_alt)
                
            # 1. If on the ground, we MUST takeoff first
            if current_alt < 2.0:
                self.ui_callback(msg_log=f"[SYSTEM] Drone grounded. Auto-Takeoff sequence required.", log_type="system")
                self.vehicle.mav.command_long_send(self.vehicle.target_system, self.vehicle.target_component, mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 4, 0, 0, 0, 0, 0)
                time.sleep(1.0)
                self.vehicle.mav.command_long_send(self.vehicle.target_system, self.vehicle.target_component, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)
                time.sleep(2.0)
                self.vehicle.mav.command_long_send(self.vehicle.target_system, self.vehicle.target_component, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, float(self.target_alt))
                
                # Wait until drone actually gets into the air (at least 3 meters)
                self.ui_callback(msg_log=f"[SYSTEM] Climbing to safe altitude ({self.target_alt}m)...", log_type="system")
                for _ in range(20): # Max wait 20 seconds
                    if self.vfr_alt - self.home_alt >= 3.0:
                        break
                    time.sleep(1.0)
            else:
                # Already flying, just make sure we are in GUIDED mode
                self.vehicle.mav.command_long_send(
                    self.vehicle.target_system, self.vehicle.target_component,
                    mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
                    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 4, 0, 0, 0, 0, 0
                )
                time.sleep(0.5)
            
            # 2. Command Drone to fly to Coordinate
            self.ui_callback(msg_log=f"[SYSTEM] Route Locked.", log_type="system")
            time.sleep(0.5)
            self.ui_callback(msg_log=f"[SYSTEM] Altitude Safe. Engaging forward thrusters...", log_type="system")
            self.vehicle.mav.set_position_target_global_int_send(
                0, # time_boot_ms
                self.vehicle.target_system, self.vehicle.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                0b0000111111111000, # type_mask (only use position)
                int(lat * 1e7),
                int(lon * 1e7),
                float(self.target_alt), # Use dynamic target altitude
                0, 0, 0, 0, 0, 0, 0, 0
            )
            time.sleep(0.5)
            self.ui_callback(msg_log=f"[SYSTEM] En route to target at {self.target_speed} m/s.", log_type="system")
            
        threading.Thread(target=_fly, daemon=True).start()

class CyberDefenseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("UAV Cyber Defense Dashboard")
        self.geometry("1400x900")
        self.configure(fg_color=BG_DARK)
        
        # Grid layout
        self.grid_columnconfigure(0, weight=1) # Map
        self.grid_columnconfigure(1, weight=1) # Graphs / Gauge
        self.grid_rowconfigure(0, weight=3) # Main content
        self.grid_rowconfigure(1, weight=1) # Terminal
        
        # Main Panels
        self.build_map_panel()
        self.build_info_panel()
        self.build_terminal_panel()
        
        # State Data
        self.home_location = None
        self.path_points = []
        self.path_polygon = None
        self.emergency_polygon = None
        self.drone_marker = None
        self.target_marker = None
        self.target_polygon = None
        
        # Load Custom Drone Icon
        self.drone_icon_img = ImageTk.PhotoImage(Image.open("drone_icon_safe.png").resize((50, 50)))
        
        # Matplotlib Graph Data
        self.graph_time = collections.deque(maxlen=50)
        self.graph_alt = collections.deque(maxlen=50)
        self.graph_spd = collections.deque(maxlen=50)
        self.start_time = time.time()
        
        # Start Bridge
        self.bridge = UAVDataBridge(self.bridge_callback)

    def build_map_panel(self):
        self.map_frame = ctk.CTkFrame(self, fg_color=PANEL_BG, corner_radius=0, border_width=2, border_color=NEON_CYAN)
        self.map_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Map Widget
        self.map_widget = tkintermapview.TkinterMapView(self.map_frame, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True, padx=5, pady=5)
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
        
        # Interactive Click-to-Fly Feature
        self.map_widget.add_right_click_menu_command(label="Fly to Coordinate", command=self.set_target_waypoint, pass_coords=True)

    def set_target_waypoint(self, coords):
        lat, lon = coords
        
        # 1. Place Target Marker on map
        if self.target_marker:
            self.target_marker.set_position(lat, lon)
        else:
            self.target_marker = self.map_widget.set_marker(lat, lon, text="TARGET", marker_color_circle="#fbbf24", marker_color_outside="#f59e0b")
            
        # 2. Command Backend
        self.bridge.fly_to_waypoint(lat, lon)

    def build_info_panel(self):
        self.info_frame = ctk.CTkFrame(self, fg_color=PANEL_BG, corner_radius=0)
        self.info_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # 1. Status Banner
        self.status_banner = ctk.CTkLabel(self.info_frame, text="SYSTEM SECURE", font=ctk.CTkFont(size=24, weight="bold"), text_color=SAFE_GREEN, fg_color="#000000", corner_radius=5)
        self.status_banner.pack(fill="x", padx=10, pady=10)
        
        # 2. Live Graphs (Matplotlib)
        self.fig = Figure(figsize=(5, 3), dpi=100, facecolor=PANEL_BG)
        self.ax_alt = self.fig.add_subplot(211)
        self.ax_spd = self.fig.add_subplot(212)
        
        for ax in [self.ax_alt, self.ax_spd]:
            ax.set_facecolor(BG_DARK)
            ax.tick_params(colors=TEXT_COLOR, labelsize=8)
            ax.spines['bottom'].set_color(NEON_CYAN)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color(NEON_CYAN)
            
        self.line_alt, = self.ax_alt.plot([], [], color=SAFE_GREEN, linewidth=2)
        self.line_spd, = self.ax_spd.plot([], [], color=NEON_CYAN, linewidth=2)
        self.ax_alt.set_title("Altitude (m)", color=TEXT_COLOR, fontsize=10, loc='left')
        self.ax_spd.set_title("Speed (m/s)", color=TEXT_COLOR, fontsize=10, loc='left')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.info_frame)
        # DO NOT PACK CANVAS YET!
        
        # 3. Circular Gauge & Controls (Pack to BOTTOM first so it doesn't get pushed off screen)
        bottom_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        
        # Gauge
        self.gauge_canvas = tk.Canvas(bottom_frame, width=150, height=150, bg=PANEL_BG, highlightthickness=0)
        self.gauge_canvas.pack(side="left", padx=20)
        self.draw_gauge(0.0, SAFE_GREEN)
        
        # Controls
        ctrl_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        ctrl_frame.pack(side="right", fill="both", expand=True)
        self.btn_takeoff = ctk.CTkButton(ctrl_frame, text="ARM & TAKEOFF", fg_color=BG_DARK, border_color=NEON_CYAN, border_width=2, text_color=NEON_CYAN, hover_color="#005566", command=lambda: self.bridge.send_command('TAKEOFF'))
        self.btn_takeoff.pack(fill="x", pady=(0, 5))
        self.btn_rtl = ctk.CTkButton(ctrl_frame, text="INITIATE RTL", fg_color=BG_DARK, border_color=SAFE_GREEN, border_width=2, text_color=SAFE_GREEN, hover_color="#005533", command=lambda: self.bridge.send_command('RTL'))
        self.btn_rtl.pack(fill="x", pady=5)
        self.btn_land = ctk.CTkButton(ctrl_frame, text="EMERGENCY LAND", fg_color=NEON_RED, hover_color="#880000", text_color="#ffffff", command=lambda: self.bridge.send_command('LAND'))
        self.btn_land.pack(fill="x", pady=(5, 10))
        
        # Flight Adjustment Panel
        adj_frame = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        adj_frame.pack(fill="x")
        
        # Altitude controls
        alt_frame = ctk.CTkFrame(adj_frame, fg_color="transparent")
        alt_frame.pack(side="left", expand=True, fill="x", padx=2)
        ctk.CTkButton(alt_frame, text="Alt +5m", height=24, fg_color="#334155", command=lambda: self.bridge.change_alt(5)).pack(fill="x", pady=2)
        ctk.CTkButton(alt_frame, text="Alt -5m", height=24, fg_color="#334155", command=lambda: self.bridge.change_alt(-5)).pack(fill="x", pady=2)
        
        # Speed controls
        spd_frame = ctk.CTkFrame(adj_frame, fg_color="transparent")
        spd_frame.pack(side="right", expand=True, fill="x", padx=2)
        ctk.CTkButton(spd_frame, text="Spd +2m/s", height=24, fg_color="#334155", command=lambda: self.bridge.change_speed(2)).pack(fill="x", pady=2)
        ctk.CTkButton(spd_frame, text="Spd -2m/s", height=24, fg_color="#334155", command=lambda: self.bridge.change_speed(-2)).pack(fill="x", pady=2)

        # NOW pack canvas last, so it takes whatever space is left over
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)

    def build_terminal_panel(self):
        self.term_frame = ctk.CTkFrame(self, fg_color="#000000", corner_radius=0, border_width=1, border_color="#333")
        self.term_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.term_frame.grid_columnconfigure(0, weight=1)
        self.term_frame.grid_columnconfigure(1, weight=1)
        self.term_frame.grid_rowconfigure(1, weight=1)
        
        # Left Panel (Raw Packets)
        ctk.CTkLabel(self.term_frame, text="RAW PACKET STREAM", text_color=TEXT_COLOR, font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, pady=(5,0))
        self.term_text_left = ctk.CTkTextbox(self.term_frame, fg_color="transparent", text_color=SAFE_GREEN, font=ctk.CTkFont(family="monospace", size=11))
        self.term_text_left.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # Right Panel (Command & Alert Log)
        ctk.CTkLabel(self.term_frame, text="COMMAND & ALERT LOG", text_color=TEXT_COLOR, font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=1, pady=(5,0))
        self.term_text_right = ctk.CTkTextbox(self.term_frame, fg_color="transparent", text_color=NEON_CYAN, font=ctk.CTkFont(family="monospace", size=12))
        self.term_text_right.grid(row=1, column=1, sticky="nsew", padx=10, pady=5)

    def draw_gauge(self, percentage, color):
        self.gauge_canvas.delete("all")
        # Background arc
        self.gauge_canvas.create_arc(10, 10, 140, 140, start=0, extent=180, outline="#333", width=10, style=tk.ARC)
        # Foreground arc (Note: tk.ARC starts at 3 o'clock, 180 is 9 o'clock)
        extent = -(percentage * 180) 
        self.gauge_canvas.create_arc(10, 10, 140, 140, start=180, extent=extent, outline=color, width=10, style=tk.ARC)
        # Text
        self.gauge_canvas.create_text(75, 120, text=f"{percentage*100:.1f}%", fill=color, font=("Arial", 20, "bold"))
        self.gauge_canvas.create_text(75, 140, text="ATTACK PROBABILITY", fill=TEXT_COLOR, font=("Arial", 8))

    def bridge_callback(self, telemetry=None, msg_log=None, log_type=None):
        # Schedule GUI updates safely
        if msg_log:
            self.after(0, self.update_terminal, msg_log, log_type)
        if telemetry:
            self.after(0, self.update_telemetry, *telemetry)

    def update_terminal(self, msg, log_type):
        if log_type == "packet":
            self.term_text_left.insert("end", msg + "\n")
            self.term_text_left.see("end")
        else:
            # Add timestamp to system and alert logs
            t = time.strftime("%H:%M:%S")
            self.term_text_right.insert("end", f"[{t}] {msg}\n")
            self.term_text_right.see("end")

    def update_telemetry(self, lat, lon, alt, spd, is_attack, confidence):
        current_color = NEON_RED if is_attack else SAFE_GREEN
        
        # 1. Update Gauge & Banner
        self.draw_gauge(confidence, current_color)
        if is_attack:
            self.status_banner.configure(text="⚠ ATTACK DETECTED: LSTM ANOMALY", text_color=NEON_RED, border_color=NEON_RED, border_width=2)
            self.map_frame.configure(border_color=NEON_RED)
            self.btn_takeoff.configure(state="disabled", text="LOCKED OUT")
            self.term_text_left.configure(text_color=NEON_RED)
            self.term_text_right.configure(text_color=NEON_RED)
            self.bridge.trigger_mitigation()
        
        # 2. Update Graphs (Smart Pause Feature)
        is_idle = (alt < 0.2) and (spd < 0.2) and not is_attack
        
        if not hasattr(self, 'pause_offset'):
            self.pause_offset = 0.0
            self.last_time = time.time()
            self.was_idle = False
            
        now = time.time()
        
        # If it's idle AND was already idle last tick, we freeze the graph
        if is_idle and self.was_idle:
            self.pause_offset += (now - self.last_time) # Absorb the passed time
        else:
            # We are active! Calculate active flight time
            t = now - self.start_time - self.pause_offset
            
            self.graph_time.append(t)
            self.graph_alt.append(alt)
            self.graph_spd.append(spd)
            
            self.line_alt.set_data(self.graph_time, self.graph_alt)
            self.line_spd.set_data(self.graph_time, self.graph_spd)
            
            # Add safe limits to avoid empty sequence errors
            min_alt = min(self.graph_alt) if self.graph_alt else 0
            max_alt = max(self.graph_alt) if self.graph_alt else 10
            min_spd = min(self.graph_spd) if self.graph_spd else 0
            max_spd = max(self.graph_spd) if self.graph_spd else 5
            
            self.ax_alt.set_xlim(max(0, t - 30), t + 5)
            self.ax_alt.set_ylim(min_alt - 2, max_alt + 5)
            self.ax_spd.set_xlim(max(0, t - 30), t + 5)
            self.ax_spd.set_ylim(min_spd - 2, max_spd + 5)
            self.canvas.draw()
            
        self.last_time = now
        self.was_idle = is_idle
        
        # 3. Update Map
        if lat != 0 and lon != 0:
            if not self.drone_marker:
                self.drone_marker = self.map_widget.set_marker(lat, lon, text="UAV", icon=self.drone_icon_img)
                self.map_widget.set_position(lat, lon)
                self.map_widget.set_zoom(18)
                self.home_location = (lat, lon)
            else:
                self.drone_marker.set_position(lat, lon)
            
            new_pos = (lat, lon)
            if len(self.path_points) == 0 or self.path_points[-1] != new_pos:
                self.path_points.append(new_pos)
                if self.path_polygon: self.path_polygon.delete()
                self.path_polygon = self.map_widget.set_path(self.path_points, color=NEON_CYAN, width=2)
                
            if is_attack and self.home_location:
                if self.emergency_polygon: self.emergency_polygon.delete()
                self.emergency_polygon = self.map_widget.set_path([new_pos, self.home_location], color=NEON_RED, width=3)
                
            # Draw Target Projection Line (Yellow)
            if self.target_marker:
                target_pos = self.target_marker.position
                if self.target_polygon: self.target_polygon.delete()
                self.target_polygon = self.map_widget.set_path([new_pos, target_pos], color="#fbbf24", width=2)
                
                # If drone reaches target (roughly within a tiny degree), remove it
                if abs(lat - target_pos[0]) < 0.00005 and abs(lon - target_pos[1]) < 0.00005:
                    self.target_polygon.delete()
                    self.target_polygon = None
                    self.target_marker.delete()
                    self.target_marker = None
                    self.update_terminal("[SYSTEM] Target reached. Hovering.", "system")

if __name__ == "__main__":
    app = CyberDefenseApp()
    app.mainloop()
