# UAV Cyber Defense System - Execution Guide

Follow these steps in order to launch the simulator, the AI dashboard, and test the intrusion detection system.

## Step 1: Start the ArduPilot Simulator (SITL)
Open a new terminal and run:
```bash
cd ~/ardupilot/ArduCopter && ../Tools/autotest/sim_vehicle.py -v ArduCopter -f quad --console --map
```
*Wait for the console to show "EKF2 is using GPS" before proceeding.*

---

## Step 2: Launch the IDS Dashboard
Open a second terminal and run:
```bash
cd "/home/thigan/Desktop/FYP PROJECT"
./venv/bin/python3 desktop_app.py
```
*The dashboard will connect to the simulator on UDP port 14550.*

---

## Step 3: Run Attack Simulations (Testing)
Open a third terminal and run any of the following commands to test the AI's detection and automated mitigation:

### 1. RC Hijack / Override
```bash
cd "/home/thigan/Desktop/FYP PROJECT"
./venv/bin/python3 simulate_attack.py --connect udp:127.0.0.1:14550 --attack rc_override
```

### 2. GPS Spoofing
```bash
cd "/home/thigan/Desktop/FYP PROJECT"
./venv/bin/python3 simulate_attack.py --connect udp:127.0.0.1:14550 --attack gps_spoof
```

### 3. Mode Forcing (LAND/RTL)
```bash
cd "/home/thigan/Desktop/FYP PROJECT"
./venv/bin/python3 simulate_attack.py --connect udp:127.0.0.1:14550 --attack mode_change
```

### 4. Mid-Air Disarm
```bash
cd "/home/thigan/Desktop/FYP PROJECT"
./venv/bin/python3 simulate_attack.py --connect udp:127.0.0.1:14550 --attack disarm
```

---

## Step 4: Performance Validation
To run an automated test that calculates detection probability for all 4 attacks:
```bash
cd "/home/thigan/Desktop/FYP PROJECT"
./venv/bin/python3 validate_ids.py
```
