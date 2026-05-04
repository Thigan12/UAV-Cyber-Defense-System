"""
=============================================================
  UAV Live Bridge (Flask Web Dashboard)
  Part of the UAV Cyber Defense System (MSc FYP)
  
  This is an alternative web-based dashboard using Flask + SocketIO.
  It connects to ArduPilot SITL via MAVLink and runs real-time
  5-class LSTM inference at 10Hz.
=============================================================
"""
import time
import pickle
import collections
import numpy as np
import tensorflow as tf
from pymavlink import mavutil
from flask import Flask, render_template
from flask_socketio import SocketIO # type: ignore
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uav_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Load trained ML components
print("Loading LSTM Model and Scaler...")
model = tf.keras.models.load_model('lstm_uav_model.h5')
with open('scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

# Global state for rolling window (Time Steps = 10)
TIME_STEPS = 10
rolling_window = collections.deque(maxlen=TIME_STEPS)
conf_history = collections.deque(maxlen=30)

# Global vehicle reference for sending commands
vehicle = None
startup_time = time.time()

def live_telemetry_loop():
    global vehicle
    connection_string = 'udp:127.0.0.1:14550'
    print(f"Connecting to vehicle on: {connection_string}")
    vehicle = mavutil.mavlink_connection(connection_string)
    vehicle.wait_heartbeat()
    print("Heartbeat received! Starting live inference...")
    
    # Request data stream
    vehicle.mav.request_data_stream_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL, 10, 1)

    TARGET_MESSAGES = ['GPS_RAW_INT', 'ATTITUDE', 'VFR_HUD', 'HEARTBEAT']
    current_state = np.zeros(21)
    last_sample_time = time.time()
    vfr_alt = 0.0
    home_alt = 0.0
    
    while True:
        msg = vehicle.recv_match(type=TARGET_MESSAGES, blocking=True, timeout=1.0)
        if not msg:
            continue
            
        msg_type = msg.get_type()
        
        # Update current state vector based on message (21 features)
        if msg_type == 'GPS_RAW_INT':
            current_state[0:8] = [msg.lat, msg.lon, msg.alt, msg.eph, msg.epv, msg.vel, msg.cog, msg.satellites_visible]
        elif msg_type == 'ATTITUDE':
            current_state[8:14] = [msg.roll, msg.pitch, msg.yaw, msg.rollspeed, msg.pitchspeed, msg.yawspeed]
        elif msg_type == 'VFR_HUD':
            current_state[14:19] = [msg.airspeed, msg.groundspeed, msg.heading, msg.throttle, msg.climb]
            vfr_alt = msg.alt
        elif msg_type == 'HEARTBEAT':
            current_state[19:21] = [msg.custom_mode, msg.base_mode]
            
        # 10Hz Sampling
        current_time = time.time()
        if current_time - last_sample_time < 0.1:
            continue
        last_sample_time = current_time
        
        rolling_window.append(current_state.copy())
        
        # Run inference
        is_attack = False
        confidence = 0.0
        attack_type = 0
        
        if len(rolling_window) == TIME_STEPS:
            window_scaled = scaler.transform(np.array(rolling_window))
            window_reshaped = np.reshape(window_scaled, (1, TIME_STEPS, 21))
            
            pred_array = model.predict(window_reshaped, verbose=0)[0]
            pred_class = int(np.argmax(pred_array))
            pred_prob = float(pred_array[pred_class])
            
            # Warmup: 60s before LSTM can trigger
            if time.time() - startup_time < 60:
                pred_class = 0
            
            raw_conf = 0.0 if pred_class == 0 else pred_prob
            conf_history.append(raw_conf)
            confidence = float(sum(conf_history) / len(conf_history))
            
            is_attack = bool(confidence > 0.9)
            attack_type = pred_class if is_attack else 0
            
        # Calculate altitude
        if home_alt == 0.0 and vfr_alt != 0:
            home_alt = vfr_alt
        alt = max(0.0, vfr_alt - home_alt)
        
        # Emit data to frontend
        attack_names = {
            0: "NORMAL",
            1: "RC HIJACK",
            2: "MODE FORCING",
            3: "GPS SPOOFING",
            4: "PARAMETER SABOTAGE"
        }
        
        payload = {
            'lat': float(current_state[0]) / 1e7 if current_state[0] != 0 else 0,
            'lon': float(current_state[1]) / 1e7 if current_state[1] != 0 else 0,
            'alt': alt,
            'roll': float(current_state[8]),
            'pitch': float(current_state[9]),
            'yaw': float(current_state[10]),
            'speed': float(current_state[14]),
            'throttle': float(current_state[17]),
            'is_attack': is_attack,
            'confidence': confidence,
            'attack_type': attack_type,
            'attack_name': attack_names.get(attack_type, "UNKNOWN")
        }
        socketio.emit('telemetry_update', payload)

@socketio.on('send_command')
def handle_command(data):
    global vehicle
    if vehicle is None:
        return
        
    action = data.get('action')
    print(f"Received dashboard command: {action}")
    
    if action == 'TAKEOFF':
        vehicle.mav.param_set_send(
            vehicle.target_system, vehicle.target_component,
            b'ARMING_CHECK', 0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        )
        vehicle.mav.command_long_send(vehicle.target_system, vehicle.target_component, mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 4, 0, 0, 0, 0, 0)
        vehicle.mav.command_long_send(vehicle.target_system, vehicle.target_component, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)
        vehicle.mav.command_long_send(vehicle.target_system, vehicle.target_component, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, 10)
        
    elif action == 'RTL':
        vehicle.mav.command_long_send(vehicle.target_system, vehicle.target_component, mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 6, 0, 0, 0, 0, 0)
        
    elif action == 'LAND':
        vehicle.mav.command_long_send(vehicle.target_system, vehicle.target_component, mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 9, 0, 0, 0, 0, 0)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Start background thread for MAVLink
    t = threading.Thread(target=live_telemetry_loop)
    t.daemon = True
    t.start()
    
    # Start Flask server
    print("Starting Web Dashboard on http://127.0.0.1:5000")
    socketio.run(app, host='127.0.0.1', port=5000, debug=False)
