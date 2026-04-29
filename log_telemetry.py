import time
import csv
import argparse
from pymavlink import mavutil

# Define the MAVLink messages we want to log based on the intelligence report
TARGET_MESSAGES = ['GPS_RAW_INT', 'ATTITUDE', 'VFR_HUD', 'HEARTBEAT']

def setup_csv_writer(filename):
    """Sets up the CSV file and writes the header."""
    file = open(filename, 'w', newline='')
    writer = csv.writer(file)
    
    # Define columns: Timestamp, Message Type, Data Fields..., Label (0 for normal, 1 for attack)
    header = [
        'timestamp', 'msg_type', 'lat', 'lon', 'alt', 'eph', 'epv', 'vel', 'cog', 'satellites_visible',
        'roll', 'pitch', 'yaw', 'rollspeed', 'pitchspeed', 'yawspeed',
        'airspeed', 'groundspeed', 'heading', 'throttle', 'climb',
        'custom_mode', 'type', 'autopilot', 'base_mode', 'system_status',
        'label'
    ]
    writer.writerow(header)
    return file, writer

def log_telemetry(connection_string, output_file, label, duration=None):
    """Connects to the drone and logs telemetry data to a CSV."""
    print(f"Connecting to vehicle on: {connection_string}")
    vehicle = mavutil.mavlink_connection(connection_string)
    
    # Wait for the first heartbeat
    # This sets the system and component ID of remote system for the link
    print("Waiting for heartbeat...")
    vehicle.wait_heartbeat()
    print("Heartbeat from system (system %u component %u)" % (vehicle.target_system, vehicle.target_component))
    
    # Request data streams
    # 10 Hz is a decent rate for ML dataset generation
    request_rate = 10 
    vehicle.mav.request_data_stream_send(
        vehicle.target_system, vehicle.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL, request_rate, 1)

    print(f"Logging to {output_file} (Label={label}). Press Ctrl+C to stop.")
    
    file, writer = setup_csv_writer(output_file)
    start_time = time.time()
    
    try:
        while True:
            # Check duration
            if duration and (time.time() - start_time) > duration:
                print(f"Reached {duration} seconds. Stopping log.")
                break
                
            msg = vehicle.recv_match(type=TARGET_MESSAGES, blocking=True, timeout=1.0)
            if not msg:
                continue
                
            msg_type = msg.get_type()
            ts = time.time()
            
            # Default empty row
            row = [ts, msg_type, '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', label]
            
            # Populate fields based on message type
            if msg_type == 'GPS_RAW_INT':
                # lat, lon, alt, eph, epv, vel, cog, satellites_visible
                row[2:10] = [msg.lat, msg.lon, msg.alt, msg.eph, msg.epv, msg.vel, msg.cog, msg.satellites_visible]
            elif msg_type == 'ATTITUDE':
                # roll, pitch, yaw, rollspeed, pitchspeed, yawspeed
                row[10:16] = [msg.roll, msg.pitch, msg.yaw, msg.rollspeed, msg.pitchspeed, msg.yawspeed]
            elif msg_type == 'VFR_HUD':
                # airspeed, groundspeed, heading, throttle, climb
                row[16:21] = [msg.airspeed, msg.groundspeed, msg.heading, msg.throttle, msg.climb]
            elif msg_type == 'HEARTBEAT':
                # custom_mode, type, autopilot, base_mode, system_status
                row[21:26] = [msg.custom_mode, msg.type, msg.autopilot, msg.base_mode, msg.system_status]
            
            writer.writerow(row)
            
    except KeyboardInterrupt:
        print("\nLogging stopped by user.")
    finally:
        file.close()
        print(f"Data saved to {output_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Log MAVLink Telemetry to CSV')
    parser.add_argument('--connect', default='udp:127.0.0.1:14550', help='Vehicle connection target string.')
    parser.add_argument('--out', default='normal_flight_data.csv', help='Output CSV file name.')
    parser.add_argument('--label', type=int, default=0, help='Label for ML dataset (0=Normal, 1=Attack).')
    parser.add_argument('--duration', type=int, default=None, help='Duration in seconds to log (default: infinite).')
    args = parser.parse_args()
    
    log_telemetry(args.connect, args.out, args.label, args.duration)
