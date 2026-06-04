import time
import csv
import random
import threading
import math
import numpy as np
from pymavlink import mavutil
from feature_extractor import FeatureExtractor

LABELS = {
    'normal': 0,
    'rc_hijack': 1,
    'mode_forcing': 2,
    'gps_spoof': 3,
    'disarm': 4
}

# ArduPilot SITL Default Home
BASE_LAT = -35.363262
BASE_LON = 149.165237

keep_logging = True
current_label = 0
state_dict = {}

def get_current_location(vehicle):
    if 'lat' in state_dict and 'lon' in state_dict:
        return state_dict['lat'] / 1e7, state_dict['lon'] / 1e7
    return BASE_LAT, BASE_LON

# ==========================================
# ROBUST FLIGHT CONTROLS (THE GPS/ARM FIX)
# ==========================================
def wait_for_gps_lock(vehicle):
    print("[AUTO] Waiting for 3D GPS Lock...")
    while True:
        if state_dict.get('fix_type', 0) >= 3:
            print(f"[AUTO] GPS Locked! Satellites: {state_dict.get('satellites_visible', 0)}")
            break
        time.sleep(1)

def arm_and_takeoff(vehicle, target_alt=20):
    wait_for_gps_lock(vehicle)
    
    print("[AUTO] Switching to GUIDED mode...")
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 4, 0, 0, 0, 0, 0) # GUIDED
    time.sleep(1)
    
    print("[AUTO] Disabling safety arming checks for simulation...")
    vehicle.mav.param_set_send(
        vehicle.target_system, vehicle.target_component,
        b'ARMING_CHECK', 0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
    time.sleep(1)

    print("[AUTO] Arming motors...")
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)
    
    # Wait until actually armed (read from shared state)
    while True:
        if state_dict.get('armed', 0.0) == 1.0:
            print("[AUTO] Motors Armed Successfully!")
            break
        time.sleep(1)
        
    print(f"[AUTO] Taking off to {target_alt} meters...")
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, target_alt)
        
    # Wait until altitude is reached
    while True:
        alt = state_dict.get('relative_alt', 0.0)
        if alt >= target_alt * 0.95:
            print(f"[AUTO] Reached Target Altitude: {alt:.1f}m")
            break
        time.sleep(0.5)

def force_rtl(vehicle):
    print("[AUTO] Executing RTL (Return to Launch)...")
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 6, 0, 0, 0, 0, 0) # RTL
    
    # Wait until disarmed
    print("[AUTO] Waiting for drone to land and disarm...")
    while True:
        if state_dict.get('armed', 1.0) == 0.0:
            print("[AUTO] Drone Landed and Disarmed.")
            break
        time.sleep(1)

# ==========================================
# ADVANCED WAYPOINT & SPEED CALCULATION
# ==========================================
def fly_random_waypoint(vehicle):
    """Flies the drone to a random waypoint between 50m and 150m away"""
    lat, lon = get_current_location(vehicle)
    
    # 50m to 150m roughly translates to 0.00045 to 0.00135 degrees
    distance_deg = random.uniform(0.00045, 0.00135)
    angle = random.uniform(0, 2 * math.pi)
    
    target_lat = lat + (distance_deg * math.cos(angle))
    target_lon = lon + (distance_deg * math.sin(angle))
    
    # Change speed randomly between 3 m/s (300cm/s) and 15 m/s (1500cm/s)
    speed_cms = random.choice([300, 600, 1000, 1500])
    print(f"[AUTO] Speed changed to {speed_cms/100.0} m/s")
    vehicle.mav.param_set_send(
        vehicle.target_system, vehicle.target_component,
        b'WPNAV_SPEED', speed_cms, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
    time.sleep(0.5)

    print(f"[AUTO] Flying to waypoint (Distance ~{int(distance_deg*111320)}m)...")
    vehicle.mav.set_position_target_global_int_send(
        0, vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT, 0b0000111111111000,
        int(target_lat * 1e7), int(target_lon * 1e7), 20.0,
        0, 0, 0, 0, 0, 0, 0, 0)
        
    # Calculate flight time dynamically: Time = Distance / Speed
    distance_m = distance_deg * 111320
    flight_time = (distance_m / (speed_cms / 100.0)) + 5.0 # Add 5s buffer
    return flight_time

# ==========================================
# TELEMETRY LOGGER
# ==========================================
def data_logger(vehicle, output_file):
    global keep_logging, current_label, state_dict
    extractor = FeatureExtractor()
    feature_names = extractor.get_feature_names()
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(feature_names + ['label'])
        
        vehicle.mav.request_data_stream_send(
            vehicle.target_system, vehicle.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_ALL, 10, 1)
        
        last_write = time.time()
        WATCH = ['GPS_RAW_INT', 'ATTITUDE', 'VFR_HUD', 'HEARTBEAT', 
                 'RC_CHANNELS_RAW', 'SERVO_OUTPUT_RAW', 'GLOBAL_POSITION_INT']
                 
        try:
            while keep_logging:
                msg = vehicle.recv_match(type=WATCH, blocking=True, timeout=0.05)
                if msg:
                    t = msg.get_type()
                    if t == 'GPS_RAW_INT':
                        state_dict.update({'lat': msg.lat, 'lon': msg.lon, 'alt': msg.alt, 'groundspeed': msg.vel, 'fix_type': msg.fix_type, 'satellites_visible': msg.satellites_visible})
                    elif t == 'ATTITUDE':
                        state_dict.update({'pitch': msg.pitch, 'roll': msg.roll, 'yaw': msg.yaw,
                                           'pitchspeed': msg.pitchspeed, 'rollspeed': msg.rollspeed, 'yawspeed': msg.yawspeed})
                    elif t == 'VFR_HUD':
                        state_dict.update({'airspeed': msg.airspeed, 'groundspeed': msg.groundspeed, 'alt': msg.alt,
                                           'heading': msg.heading, 'throttle': msg.throttle, 'climb': msg.climb})
                    elif t == 'RC_CHANNELS_RAW':
                        state_dict.update({'chan1_raw': msg.chan1_raw, 'chan3_raw': msg.chan3_raw})
                    elif t == 'SERVO_OUTPUT_RAW':
                        state_dict.update({'servo1_raw': msg.servo1_raw, 'servo3_raw': msg.servo3_raw})
                    elif t == 'GLOBAL_POSITION_INT':
                        state_dict['vz'] = msg.vz / 100.0
                        state_dict['relative_alt'] = msg.relative_alt / 1000.0
                    elif t == 'HEARTBEAT':
                        armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                        state_dict['armed'] = float(armed)

                now = time.time()
                if now - last_write >= 0.1:
                    last_write = now
                    if 'lat' in state_dict and 'roll' in state_dict and 'airspeed' in state_dict:
                        features = extractor.extract(state_dict)
                        writer.writerow(features + [current_label])
                        
        except KeyboardInterrupt:
            pass

# ==========================================
# DATASET GENERATION PHASES
# ==========================================
def run_normal_flight(vehicle):
    global current_label
    current_label = LABELS['normal']
    print("\n" + "="*40)
    print(" PHASE 0: NORMAL FLIGHT (Including 1KM Long Haul)")
    print("="*40)
    
    for i in range(5):
        print(f"\n--- Normal Flight Run {i+1}/5 ---")
        arm_and_takeoff(vehicle, random.choice([20, 30, 40]))
        
        # Trial 1 is the 1-Kilometer Long Haul!
        if i == 0:
            print("[AUTO] Initiating 1-Kilometer Long Haul Cruise...")
            lat, lon = get_current_location(vehicle)
            # 1km = 0.00898 degrees
            target_lat = lat + 0.00898 
            target_lon = lon
            
            # Fast speed for long haul (15 m/s)
            vehicle.mav.param_set_send(
                vehicle.target_system, vehicle.target_component,
                b'WPNAV_SPEED', 1500, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
            time.sleep(0.5)
            
            vehicle.mav.set_position_target_global_int_send(
                0, vehicle.target_system, vehicle.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT, 0b0000111111111000,
                int(target_lat * 1e7), int(target_lon * 1e7), 30.0,
                0, 0, 0, 0, 0, 0, 0, 0)
            
            # 1000m / 15m/s = ~66 seconds. Wait 75s to ensure arrival.
            time.sleep(75)
        else:
            # Stage 1: Fly Forward (Standard Cruise 50m - 150m)
            flight_time = fly_random_waypoint(vehicle)
            time.sleep(flight_time) 
        
        # Stage 2: Hover
        print("[AUTO] Hovering...")
        vehicle.mav.command_long_send(
            vehicle.target_system, vehicle.target_component,
            mavutil.mavlink.MAV_CMD_NAV_LOITER_UNLIM, 0, 0, 0, 0, 0, 0, 0, 0)
        time.sleep(20) 
        
        # Stage 3: Return
        force_rtl(vehicle)

def execute_attack_stage(vehicle):
    """Simulates a random stage of flight before an attack triggers"""
    stage = random.choice(["hover", "cruise", "long_cruise", "climb"])
    if stage == "hover":
        print("[STAGE] Drone is Hovering...")
        time.sleep(5)
    elif stage == "cruise":
        print("[STAGE] Drone is Cruising (Short Range)...")
        fly_random_waypoint(vehicle)
        time.sleep(10) # Attack mid-flight
    elif stage == "long_cruise":
        print("[STAGE] Drone is on a 1-Kilometer Mission...")
        lat, lon = get_current_location(vehicle)
        # 1km away
        target_lat = lat + 0.00898 
        vehicle.mav.param_set_send(
            vehicle.target_system, vehicle.target_component,
            b'WPNAV_SPEED', 1500, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
        time.sleep(0.5)
        vehicle.mav.set_position_target_global_int_send(
            0, vehicle.target_system, vehicle.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT, 0b0000111111111000,
            int(target_lat * 1e7), int(lon * 1e7), 30.0,
            0, 0, 0, 0, 0, 0, 0, 0)
        # Wait 20 to 40 seconds so the attack happens when it's FAR away from base!
        time.sleep(random.randint(20, 40)) 
    elif stage == "climb":
        print("[STAGE] Drone is Climbing...")
        vehicle.mav.command_long_send(
            vehicle.target_system, vehicle.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, random.choice([30, 40, 50]))
        time.sleep(3) # Attack while climbing

def run_rc_hijack(vehicle):
    global current_label
    print("\n" + "="*40)
    print(" PHASE 1: RC HIJACK (15 Trials)")
    print("="*40)
    for trial in range(15):
        current_label = LABELS['normal']
        arm_and_takeoff(vehicle, 20)
        execute_attack_stage(vehicle)
        
        current_label = LABELS['rc_hijack']
        duration = random.randint(10, 30)
        print(f"--> Trial {trial+1}/15: RC Hijack for {duration}s")
        
        vehicle.mav.command_long_send(
            vehicle.target_system, vehicle.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 0, 0, 0, 0, 0, 0) # Force STABILIZE
        time.sleep(0.5)
        
        ch1 = random.choice([1000, 1900, 2000])
        ch3 = random.choice([1000, 1900, 2000])
        
        end_time = time.time() + duration
        while time.time() < end_time:
            vehicle.mav.rc_channels_override_send(
                vehicle.target_system, vehicle.target_component,
                ch1, 1500, ch3, 1500, 0, 0, 0, 0)
            time.sleep(0.1)
            
        vehicle.mav.rc_channels_override_send(
            vehicle.target_system, vehicle.target_component,
            0, 0, 0, 0, 0, 0, 0, 0) # Release
        
        current_label = LABELS['normal']
        force_rtl(vehicle)

def run_mode_forcing(vehicle):
    global current_label
    print("\n" + "="*40)
    print(" PHASE 2: MODE FORCING (15 Trials)")
    print("="*40)
    for trial in range(15):
        current_label = LABELS['normal']
        arm_and_takeoff(vehicle, 20)
        execute_attack_stage(vehicle)
        
        current_label = LABELS['mode_forcing']
        duration = random.randint(8, 25)
        print(f"--> Trial {trial+1}/15: Mode Forcing for {duration}s")
        
        end_time = time.time() + duration
        while time.time() < end_time:
            m = random.choice([0, 6, 9, 16]) # Random malicious modes
            vehicle.mav.command_long_send(
                vehicle.target_system, vehicle.target_component,
                mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, m, 0, 0, 0, 0, 0)
            time.sleep(random.uniform(2.0, 5.0))
            
        current_label = LABELS['normal']
        force_rtl(vehicle)

def run_gps_spoof(vehicle):
    global current_label
    print("\n" + "="*40)
    print(" PHASE 3: GPS SPOOFING (15 Trials)")
    print("="*40)
    for trial in range(15):
        current_label = LABELS['normal']
        arm_and_takeoff(vehicle, 20)
        execute_attack_stage(vehicle)
        
        current_label = LABELS['gps_spoof']
        duration = random.randint(15, 40)
        
        lat_offset = random.uniform(0.03, 0.09) * random.choice([1, -1])
        lon_offset = random.uniform(0.03, 0.09) * random.choice([1, -1])
        fake_lat = BASE_LAT + lat_offset
        fake_lon = BASE_LON + lon_offset
        
        print(f"--> Trial {trial+1}/15: GPS Spoof for {duration}s (Offset: {lat_offset:.3f})")
        
        end_time = time.time() + duration
        while time.time() < end_time:
            vehicle.mav.set_position_target_global_int_send(
                0, vehicle.target_system, vehicle.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                0b0000111111111000,
                int(fake_lat * 1e7), int(fake_lon * 1e7), 50.0,
                0, 0, 0, 0, 0, 0, 0, 0)
            time.sleep(0.5)
            
        current_label = LABELS['normal']
        force_rtl(vehicle)

def run_disarm(vehicle):
    global current_label
    print("\n" + "="*40)
    print(" PHASE 4: MID-AIR DISARM (15 Trials)")
    print("="*40)
    for trial in range(15):
        current_label = LABELS['normal']
        arm_and_takeoff(vehicle, random.choice([30, 40, 50])) # High alt so it falls safely
        execute_attack_stage(vehicle)
        
        current_label = LABELS['disarm']
        print(f"--> Trial {trial+1}/15: Disarm Attack")
        
        if random.random() > 0.5:
            vehicle.mav.command_long_send(
                vehicle.target_system, vehicle.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
                0, 21196, 0, 0, 0, 0, 0)
        else:
            vehicle.mav.param_set_send(
                vehicle.target_system, vehicle.target_component,
                b'ARMING_CHECK', 1, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
            time.sleep(0.1)
            vehicle.mav.command_long_send(
                vehicle.target_system, vehicle.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
                0, 0, 0, 0, 0, 0, 0)
                
        time.sleep(8) # Record falling physics
        
        current_label = LABELS['normal']
        # Re-arm mid-air and fly home
        vehicle.mav.param_set_send(
            vehicle.target_system, vehicle.target_component,
            b'ARMING_CHECK', 0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
        time.sleep(0.5)
        vehicle.mav.command_long_send(
            vehicle.target_system, vehicle.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
            1, 0, 0, 0, 0, 0, 0)
        time.sleep(1)
        force_rtl(vehicle)


if __name__ == '__main__':
    print("[*] Connecting to SITL for Ultimate Dataset Generation...")
    vehicle = mavutil.mavlink_connection('udp:127.0.0.1:14550')
    vehicle.wait_heartbeat()
    print("[*] Connected! Target system: 1")
    
    output_filename = "perfect_dataset_v2.csv"
    
    log_thread = threading.Thread(target=data_logger, args=(vehicle, output_filename))
    log_thread.daemon = True
    log_thread.start()
    
    try:
        run_normal_flight(vehicle)
        run_rc_hijack(vehicle)
        run_mode_forcing(vehicle)
        run_gps_spoof(vehicle)
        run_disarm(vehicle)
    except KeyboardInterrupt:
        print("\n[!] Sequence interrupted by user.")
    
    keep_logging = False
    print(f"\n[★] Phase 2 Success! Dataset saved to {output_filename}")
