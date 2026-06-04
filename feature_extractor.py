import numpy as np
from collections import deque

class FeatureExtractor:
    def __init__(self):
        self.prev_lat = None
        self.prev_lon = None
        self.prev_alt = None
        self.prev_speed = None
        
        # Store last 5 readings for rate-of-change features
        self.alt_history = deque(maxlen=5)
        self.speed_history = deque(maxlen=5)

    def extract(self, telemetry_dict):
        """
        Returns exactly a 26-feature vector.
        telemetry_dict must contain merged fields from:
        GPS_RAW_INT, ATTITUDE, VFR_HUD, HEARTBEAT,
        RC_CHANNELS_RAW, SERVO_OUTPUT_RAW, GLOBAL_POSITION_INT
        """
        # Convert raw coordinates if they are in 1e7 format, else use directly
        lat = telemetry_dict.get('lat', 0)
        lon = telemetry_dict.get('lon', 0)
        # Handle 1e7 format common in MAVLink
        if abs(lat) > 1000: lat /= 1e7
        if abs(lon) > 1000: lon /= 1e7
        
        alt = telemetry_dict.get('alt', 0)
        groundspeed = telemetry_dict.get('groundspeed', 0)

        # ── Derived: GPS jump (Attack 3 signal) ──────────────
        if self.prev_lat is not None:
            gps_lat_delta = abs(lat - self.prev_lat)
            gps_lon_delta = abs(lon - self.prev_lon)
            gps_jump = np.sqrt(gps_lat_delta**2 + gps_lon_delta**2)
        else:
            gps_lat_delta = 0.0
            gps_lon_delta = 0.0
            gps_jump = 0.0

        # ── Derived: altitude change rate (Attack 2 signal) ──
        alt_delta = (alt - self.prev_alt) if self.prev_alt is not None else 0.0
        self.alt_history.append(alt)
        alt_trend = (self.alt_history[-1] - self.alt_history[0]) \
                    if len(self.alt_history) == 5 else 0.0

        # ── Derived: speed change rate (Attack 1+2 signal) ───
        speed_delta = (groundspeed - self.prev_speed) \
                      if self.prev_speed is not None else 0.0

        # Update previous values for the next tick
        self.prev_lat, self.prev_lon = lat, lon
        self.prev_alt = alt
        self.prev_speed = groundspeed

        # STRICT 26-FEATURE ORDER
        features = {
            # ── 14 Original core physics features ────────────────
            'alt':              alt,
            'groundspeed':      groundspeed,
            'pitch':            telemetry_dict.get('pitch', 0),
            'roll':             telemetry_dict.get('roll', 0),
            'yaw':              telemetry_dict.get('yaw', 0),
            'pitchspeed':       telemetry_dict.get('pitchspeed', 0),
            'rollspeed':        telemetry_dict.get('rollspeed', 0),
            'yawspeed':         telemetry_dict.get('yawspeed', 0),
            'climb':            telemetry_dict.get('climb', 0),
            'throttle':         telemetry_dict.get('throttle', 0),
            'airspeed':         telemetry_dict.get('airspeed', 0),
            'lat':              lat,
            'lon':              lon,
            'heading':          telemetry_dict.get('heading', 0),

            # ── 2 NEW: RC raw channels (Attack 1 — RC hijack) ───
            'ch1_roll_raw':     telemetry_dict.get('chan1_raw', 1500),
            'ch3_throttle_raw': telemetry_dict.get('chan3_raw', 1500),

            # ── 4 NEW: Vertical / Altitude Velocity (Attack 2 — Mode Force)
            'vz':               telemetry_dict.get('vz', 0),
            'alt_delta':        alt_delta,
            'alt_trend_5tick':  alt_trend,
            'speed_delta':      speed_delta,

            # ── 3 NEW: GPS Jumps (Attack 3 — GPS Spoof) ──────────
            'gps_lat_delta':      gps_lat_delta,
            'gps_lon_delta':      gps_lon_delta,
            'gps_jump_magnitude': gps_jump,

            # ── 3 NEW: Motor/Armed States (Attack 4 — Disarm) ────
            'armed_state':      float(telemetry_dict.get('armed', 1)),
            'servo1_out':       telemetry_dict.get('servo1_raw', 1500),
            'servo3_out':       telemetry_dict.get('servo3_raw', 1500),
        }

        # Ensure exactly 26 features are returned
        return list(features.values())

    def get_feature_names(self):
        return [
            'alt', 'groundspeed', 'pitch', 'roll', 'yaw',
            'pitchspeed', 'rollspeed', 'yawspeed', 'climb', 'throttle',
            'airspeed', 'lat', 'lon', 'heading',
            'ch1_roll_raw', 'ch3_throttle_raw',
            'vz', 'alt_delta', 'alt_trend_5tick', 'speed_delta',
            'gps_lat_delta', 'gps_lon_delta', 'gps_jump_magnitude',
            'armed_state', 'servo1_out', 'servo3_out',
        ]
