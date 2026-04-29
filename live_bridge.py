import time
import pickle
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
rolling_window = []

def get_empty_state():
    # Returns an empty state array matching the 19 features used in training
    return np.zeros(19)

# Global vehicle reference for sending commands
vehicle = None

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
    current_state = get_empty_state()
    
    while True:
        msg = vehicle.recv_match(type=TARGET_MESSAGES, blocking=True, timeout=1.0)
        if not msg:
            continue
            
        msg_type = msg.get_type()
        
        # Update current state vector based on message
        # Indices match the preprocessing step in train_models.py
        if msg_type == 'GPS_RAW_INT':
            current_state[0:8] = [msg.lat, msg.lon, msg.alt, msg.eph, msg.epv, msg.vel, msg.cog, msg.satellites_visible]
        elif msg_type == 'ATTITUDE':
            current_state[8:14] = [msg.roll, msg.pitch, msg.yaw, msg.rollspeed, msg.pitchspeed, msg.yawspeed]
        elif msg_type == 'VFR_HUD':
            current_state[14:19] = [msg.airspeed, msg.groundspeed, msg.heading, msg.throttle, msg.climb]
            
        # Add to rolling window
        rolling_window.append(current_state.copy())
        
        if len(rolling_window) > TIME_STEPS:
            rolling_window.pop(0)
            
        # If we have a full window, run inference
        is_attack = False
        confidence = 0.0
        
        if len(rolling_window) == TIME_STEPS:
            # Scale data
            window_scaled = scaler.transform(np.array(rolling_window))
            # Reshape to (1, time_steps, features)
            window_reshaped = np.reshape(window_scaled, (1, TIME_STEPS, 19))
            
            # Predict
            prediction = model.predict(window_reshaped, verbose=0)[0][0]
            is_attack = bool(prediction > 0.5)
            confidence = float(prediction)
            
        # Emit data to frontend
        payload = {
            'lat': float(current_state[0]) / 1e7 if current_state[0] != 0 else 0, # MAVLink GPS is *1e7
            'lon': float(current_state[1]) / 1e7 if current_state[1] != 0 else 0,
            'alt': float(current_state[2]) / 1000.0, # mm to meters
            'roll': float(current_state[8]),
            'pitch': float(current_state[9]),
            'yaw': float(current_state[10]),
            'speed': float(current_state[14]),
            'throttle': float(current_state[17]),
            'is_attack': is_attack,
            'confidence': confidence
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
        # Set GUIDED mode (4)
        vehicle.mav.command_long_send(vehicle.target_system, vehicle.target_component, mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 4, 0, 0, 0, 0, 0)
        # Arm Motors (1)
        vehicle.mav.command_long_send(vehicle.target_system, vehicle.target_component, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)
        # Takeoff to 10m altitude
        vehicle.mav.command_long_send(vehicle.target_system, vehicle.target_component, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, 10)
        
    elif action == 'RTL':
        # Set RTL mode (6)
        vehicle.mav.command_long_send(vehicle.target_system, vehicle.target_component, mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 6, 0, 0, 0, 0, 0)
        
    elif action == 'LAND':
        # Set LAND mode (9)
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
