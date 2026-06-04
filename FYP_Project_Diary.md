# UAV Cyber-Physical Intrusion Detection System
## Complete Project Diary & Thesis Reference Guide
### Author: Thigan | Date: May 2026

---

## 1. PROJECT OVERVIEW

**Title:** Real-Time Autonomous Cyber-Physical Intrusion Detection for Unmanned Aerial Vehicles Using Bidirectional LSTM with Zero-Trust Mitigation

**Objective:** Build a system where a UAV can autonomously detect 4 types of cyber-attacks in real-time using deep learning, sever communication with a compromised command center, and fly itself home safely.

**Core Innovation:** Unlike traditional network-based IDS, this system monitors the **physical behavior** of the drone (how it moves, tilts, accelerates) rather than network packets. A hacker can hide their network traffic, but they cannot hide the physical consequences of their attack.

---

## 2. TECHNOLOGY STACK

| Component | Technology | Purpose |
|---|---|---|
| Simulator | ArduPilot SITL | Simulates a real Copter on `udp:127.0.0.1:14550` |
| Protocol | MAVLink v2 (pymavlink) | Drone communication protocol |
| AI Framework | TensorFlow / Keras | Bidirectional LSTM neural network |
| Balancing | imbalanced-learn (SMOTE) | Synthetic Minority Over-sampling |
| Scaling | scikit-learn (StandardScaler) | Feature normalization |
| Dashboard | PyQt5 + Matplotlib | Real-time monitoring GUI |
| Language | Python 3.12 | All modules |
| Version Control | Git + GitHub | Branch: `feature/phase1-26-features` |

### Installed Packages
```bash
pip install pymavlink tensorflow scikit-learn imbalanced-learn pandas numpy matplotlib PyQt5
```

---

## 3. THE 5-PHASE ARCHITECTURE

### Phase 1: Feature Engineering (COMPLETED)
**File:** `feature_extractor.py`

We upgraded from a basic 19-feature model to a **26-feature vector**. The key design decision was to **remove `flight_mode`** from the features entirely. Why? Because when a human operator triggers RTL (Return to Launch) manually, the old model would see the mode change and falsely classify it as a "Mode Forcing" attack. By removing flight_mode and relying purely on physics, the AI only reacts to abnormal physical movement, not legitimate operator commands.

#### The 26 Features (Grouped by Signal Type)

**Group A — 14 Core Physics Features:**
| # | Feature | MAVLink Source | What It Measures |
|---|---------|---------------|-----------------|
| 1 | `alt` | VFR_HUD | Altitude (meters) |
| 2 | `groundspeed` | GPS_RAW_INT | Ground speed (m/s) |
| 3 | `pitch` | ATTITUDE | Forward/backward tilt (radians) |
| 4 | `roll` | ATTITUDE | Left/right tilt (radians) |
| 5 | `yaw` | ATTITUDE | Compass heading (radians) |
| 6 | `pitchspeed` | ATTITUDE | Rate of pitch change |
| 7 | `rollspeed` | ATTITUDE | Rate of roll change |
| 8 | `yawspeed` | ATTITUDE | Rate of yaw change |
| 9 | `climb` | VFR_HUD | Vertical speed (m/s) |
| 10 | `throttle` | VFR_HUD | Motor power (0-100%) |
| 11 | `airspeed` | VFR_HUD | Airspeed (m/s) |
| 12 | `lat` | GPS_RAW_INT | Latitude |
| 13 | `lon` | GPS_RAW_INT | Longitude |
| 14 | `heading` | VFR_HUD | Compass heading (degrees) |

**Group B — 2 RC Hardware Features (RC Hijack Detection):**
| # | Feature | MAVLink Source | What It Measures |
|---|---------|---------------|-----------------|
| 15 | `ch1_roll_raw` | RC_CHANNELS_RAW | Raw roll stick value (1000-2000) |
| 16 | `ch3_throttle_raw` | RC_CHANNELS_RAW | Raw throttle stick value (1000-2000) |

**Group C — 4 Delta/Rate Features (Mode Forcing Detection):**
| # | Feature | MAVLink Source | What It Measures |
|---|---------|---------------|-----------------|
| 17 | `vz` | GLOBAL_POSITION_INT | Vertical velocity (m/s) |
| 18 | `alt_delta` | Computed | Altitude change since last tick |
| 19 | `alt_trend_5tick` | Computed (deque) | Altitude trend over last 5 readings |
| 20 | `speed_delta` | Computed | Speed change since last tick |

**Group D — 3 GPS Jump Features (GPS Spoofing Detection):**
| # | Feature | MAVLink Source | What It Measures |
|---|---------|---------------|-----------------|
| 21 | `gps_lat_delta` | Computed | Latitude jump since last tick |
| 22 | `gps_lon_delta` | Computed | Longitude jump since last tick |
| 23 | `gps_jump_magnitude` | Computed (√) | Euclidean distance of GPS jump |

**Group E — 3 Motor/Armed Features (Disarm Detection):**
| # | Feature | MAVLink Source | What It Measures |
|---|---------|---------------|-----------------|
| 24 | `armed_state` | HEARTBEAT | 1.0 = armed, 0.0 = disarmed |
| 25 | `servo1_out` | SERVO_OUTPUT_RAW | Motor 1 PWM output |
| 26 | `servo3_out` | SERVO_OUTPUT_RAW | Motor 3 PWM output |

---

### Phase 2: Dataset Generation (COMPLETED)
**File:** `auto_generate_dataset.py`
**Output:** `perfect_dataset_v2.csv` (41,199 rows × 27 columns)

#### Attack Classes
| Label | Attack Type | What Happens |
|-------|------------|-------------|
| 0 | Normal Flight | Safe flying, hovering, waypoint navigation |
| 1 | RC Hijack | Attacker overrides RC channels with extreme values |
| 2 | Mode Forcing | Attacker rapidly switches flight modes (STABILIZE, RTL, LAND) |
| 3 | GPS Spoofing | Attacker injects fake GPS coordinates (3-9 km offset) |
| 4 | Mid-Air Disarm | Attacker sends emergency motor kill command mid-flight |

#### Dataset Generation Protocol
- **Normal Flight:** 5 runs including one 1-Kilometer continuous cruise. Waypoints randomized between 50m-150m. Speed dynamically varied (3, 6, 10, 15 m/s).
- **Each Attack Type:** 15 independent trials with randomized duration, intensity, and attack method variants.
- **Attack Stage Variance:** Before each attack trial, the drone is randomly placed in one of 4 stages: Hovering, Short Cruise, 1km Long Cruise, or Climbing. This prevents the AI from associating attacks only with hovering drones.
- **Logging Rate:** 10 Hz (10 rows per second).

#### Critical Bugs Fixed During Phase 2
1. **GPS Lock Race Condition:** The original script sent ARM commands before SITL had a GPS satellite lock, causing the drone to reject arming. Fixed by implementing `wait_for_gps_lock()` that polls `fix_type >= 3`.
2. **Thread Message Stealing:** Both the Logger thread and Commander thread were calling `vehicle.recv_match()`, causing them to steal MAVLink messages from each other. Fixed by making the Logger thread the sole listener, writing to a shared `state_dict` that the Commander reads.
3. **Altitude Verification:** Added a loop that checks `relative_alt` against target altitude before proceeding, ensuring the drone is truly airborne.

#### Sample CSV Row (Normal Flight)
```
alt, groundspeed, pitch, roll, yaw, pitchspeed, rollspeed, yawspeed, climb, throttle, airspeed, lat, lon, heading, ch1_roll_raw, ch3_throttle_raw, vz, alt_delta, alt_trend_5tick, speed_delta, gps_lat_delta, gps_lon_delta, gps_jump_magnitude, armed_state, servo1_out, servo3_out, label
568720, 0, 0.002, 0.003, 0.617, 0.0003, 0.0003, 0.001, 0.02, 0, 0.029, -35.356, 149.174, 35, 1500, 1500, -0.02, 0, 0, 0, 0.0, 0.0, 0.0, 1.0, 1000, 1000, 0
```

---

### Phase 3: Model Training (IN PROGRESS)
**File:** `train_models.py`
**Output:** `lstm_uav_v2.h5` + `scaler_v2.pkl`

#### Architecture: Bidirectional LSTM
```
Input Shape: (50 timesteps, 26 features)
    ↓
Bidirectional(LSTM(128, return_sequences=True))
Dropout(0.3) → BatchNormalization()
    ↓
Bidirectional(LSTM(64))
Dropout(0.3) → BatchNormalization()
    ↓
Dense(32, relu) → Dropout(0.2)
    ↓
Dense(5, softmax) → [Normal, RC_Hijack, Mode_Force, GPS_Spoof, Disarm]
```

#### Deep Learning Intuition (How the AI "Thinks")
To achieve real-time cyber-physical detection, the AI does not look at single rows of data (like a photograph). Instead, it groups 50 rows together to create a **"5-second physics movie"**. 
* **Bidirectional Reading:** The LSTM Neural Network reads this 5-second movie forwards and backwards. This allows it to easily spot the exact millisecond a hacker forces a sudden GPS jump or motor failure by contrasting the anomaly with the safe data immediately surrounding it.
* **Attack Fingerprints:** The AI learns the physical signature of each cyber-attack. For example, it learns that if `ch1_roll_raw` suddenly spikes to 2000 while the drone is in a smooth cruise, it's an RC Hijack. If `armed_state` drops to 0 while `alt` is still 50 meters, it's a Mid-Air Disarm. It compresses this knowledge into a lightweight `.h5` brain file for live deployment.

#### SMOTE (Synthetic Minority Over-sampling)
Because ~80% of the dataset is Normal flight data, a naive model could achieve 80% accuracy by always predicting "Normal." SMOTE generates synthetic attack samples by interpolating between real attack samples, perfectly balancing all 5 classes before training. Critical rule: SMOTE is applied ONLY to training data, NEVER to test data (prevents data leakage).

#### Zero-Trust Class Weights
Even after SMOTE balancing, we apply an additional 3x penalty multiplier on all attack classes. This forces the model to be paranoid — it would rather trigger a false alarm than miss a real attack.

#### Training Configuration
| Parameter | Value | Reason |
|-----------|-------|--------|
| Time Steps | 50 | 5 seconds at 10Hz |
| Batch Size | 128 | Stable gradient updates |
| Max Epochs | 30 | With EarlyStopping |
| EarlyStopping patience | 5 | Prevents overfitting |
| ReduceLROnPlateau | factor=0.5, patience=2 | Adaptive learning rate |
| Train/Test Split | 80/20 | Stratified by class |

#### Final Validation Results (The Zero-Trust Triumph)
The model was evaluated against an untouched, un-SMOTEd validation dataset of 8,230 sequences. The results absolutely prove our core thesis hypothesis:

```text
CLASSIFICATION REPORT (Zero-Trust Validation):
              precision    recall  f1-score   support

      Normal       1.00      0.93      0.96      6310
   RC_Hijack       0.74      1.00      0.85       520
  Mode_Force       0.82      1.00      0.90       529
   GPS_Spoof       0.96      1.00      0.98       668
      Disarm       0.64      1.00      0.78       203

    accuracy                           0.95      8230

CONFUSION MATRIX:
[[5875  178  115   26  116]
 [   2  518    0    0    0]
 [   0    0  529    0    0]
 [   0    0    0  668    0]
 [   0    0    0    0  203]]
```

*   **100% Attack Recall:** The AI successfully caught **100%** of Mode Forces, **100%** of GPS Spoofs, **100%** of Mid-Air Disarms, and **99.6%** of RC Hijacks. It missed a grand total of 2 attacks out of 1,920 malicious injections.
*   **The Paranoia Trade-off:** The model achieved 93% recall on Normal flight (meaning a 7% false positive rate). Because we intentionally applied the 3x penalty weight to attack classes, we explicitly programmed the AI to be paranoid. In a Zero-Trust military architecture, an occasional false alarm is infinitely better than a single undetected attack. This is a massive success.

#### How to Read the AI Metrics (For Thesis Report)
To understand the AI's performance, we look at two mathematical tables: the **Classification Report** and the **Confusion Matrix**.

**1. The Classification Report (Precision vs. Recall)**
*   **Recall** answers: *"Out of all the real attacks that happened, how many did the AI catch?"*
    *   Our AI scored **1.00 (100%)** recall on Mode_Force, GPS_Spoof, and Disarm. It scored 0.996 (rounds to 1.00) on RC_Hijack. This means it almost never misses an attack.
*   **Precision** answers: *"When the AI yells 'ATTACK!', how often is it actually right?"*
    *   Our AI scored lower on precision (e.g., 0.64 for Disarm). This is the *Zero-Trust Paranoia* in action. Because we mathematically forced the AI to be hyper-sensitive (using the 3x class weights), it sometimes yells "ATTACK!" during a slightly bumpy normal flight. 

**2. The Confusion Matrix**
The Confusion Matrix shows exactly where the AI made mistakes. 
*   **The Rows** are the *Actual Truth* (what was really happening).
*   **The Columns** are the *AI's Prediction* (what the AI thought was happening).
*   **The Diagonal Line** (5875, 518, 529, 668, 203) represents perfect, correct predictions.

**Breaking down the matrix:**
*   **Row 1 (Normal Flight):** Out of 6,310 perfectly safe flights, the AI correctly identified 5,875 of them. However, it falsely panicked and called 178 of them an RC Hijack, 115 a Mode Force, 26 a GPS Spoof, and 116 a Disarm. (This is the 7% False Alarm rate).
*   **Row 2 (RC Hijack):** Out of 520 real hijack attacks, the AI caught 518 of them perfectly, and only missed 2 (mistaking them for normal flight).
*   **Row 3 (Mode Force):** Out of 529 real mode force attacks, the AI caught 529. **0 missed.**
*   **Row 4 (GPS Spoof):** Out of 668 real spoofing attacks, the AI caught 668. **0 missed.**
*   **Row 5 (Disarm):** Out of 203 real mid-air disarms, the AI caught 203. **0 missed.**

---

### Phase 4: Zero-Trust Telemetry Bridge (ARCHITECTURAL PIVOT)
**File:** `desktop_app.py` (Class: `UAVDataBridge`)

**Architectural Pivot (Abandoning `live_bridge.py`):** 
Initially, we planned to use a standalone script (`live_bridge.py`) to process telemetry and forward it to the dashboard. We discovered this was inefficient and caused unnecessary latency. Instead, we built the bridge *directly* into the dashboard as the `UAVDataBridge` class. This allows the AI to process the 26 features natively within the UI's memory space.

#### The 7 Cyber-Security Telemetry Packets
To feed the AI brain in real-time, the dashboard aggressively filters the MAVLink stream and listens exclusively to 7 specific packets. Each packet is critical for detecting specific cyber-physical anomalies:

1.  **`GPS_RAW_INT`**: Provides raw latitude, longitude, and GPS altitude. *Security Purpose:* Crucial for calculating `gps_jump_magnitude` to instantly detect **GPS Spoofing / Silent Reroute** attacks.
2.  **`ATTITUDE`**: Provides the drone's 3D orientation (pitch, roll, yaw) and angular velocities. *Security Purpose:* Detects the physical turbulence caused when a hacker's inputs fight against the legitimate autopilot.
3.  **`VFR_HUD`**: Provides highly filtered, smooth data for airspeed, groundspeed, throttle percentage, and climb rate. *Security Purpose:* Used to detect unnatural throttle cuts or sudden drops in speed during a cruise.
4.  **`HEARTBEAT`**: Broadcasts the drone's active flight mode (GUIDED, RTL, LAND) and armed state. *Security Purpose:* Used to track connection status and verify if the drone is actively armed.
5.  **`RC_CHANNELS_RAW`**: Provides the raw, unadulterated radio signals from the pilot's physical remote control. *Security Purpose:* The absolute most critical packet for detecting **RC Hijack (Crash Override)** attacks.
6.  **`SERVO_OUTPUT_RAW`**: Provides the actual PWM electrical signals being sent to the drone's physical motors. *Security Purpose:* Crucial for detecting **Mid-Air Disarm Sabotage** (detecting when the motors instantly cut power while the drone is still 50 meters in the air).
7.  **`GLOBAL_POSITION_INT`**: Provides the drone's vertical velocity (`vz`). *Security Purpose:* Used to calculate the `alt_trend` (falling/climbing) to detect **Unauthorized Mode Forcing** (e.g., forcing a drone into LAND mode).

#### Multi-Threaded Architecture
```
Thread 1: UI Mainloop        → Renders the Map and Matplotlib Graphs safely
Thread 2: Telemetry Loop     → Non-blocking MAVLink 10Hz listener via UAVDataBridge
Thread 3: Defense Protocol   → Asynchronous Zero-Trust RTL execution
```

#### Zero-Trust Lockdown Protocol
When the AI detects an attack with high confidence for 3 consecutive ticks:
1. Override all external RC inputs (lock out the hacker)
2. Force the flight controller into RTL mode
3. Ignore all command center overrides until safe landing
4. The drone flies home using only its internal navigation

---

### Phase 5: Dashboard GUI (PLANNED)
**File:** `desktop_app.py`

#### Planned Features
- **Threat Alert:** Full-screen warning: "THREAT DETECTED. COMMUNICATION SEVERED."
- **Auto-Return Map:** Red line drawn from attack location to Home Base
- **Live Tracking:** Drone icon follows the return path in real-time
- **Attack Classification:** Shows exact attack type and AI confidence percentage

---

## 4. KEY DESIGN DECISIONS

| Decision | Rationale |
|----------|-----------|
| Removed `flight_mode` from features | Prevents false positives when operator manually triggers RTL/LAND |
| 10Hz logging rate | Matches MAVLink stream rate; gives 100ms resolution |
| 50-timestep window (5 seconds) | Long enough to capture attack signatures, short enough for real-time |
| Thread-safe shared `state_dict` | Prevents message stealing between Logger and Commander threads |
| SMOTE before training, not before split | Prevents data leakage (test data must be pure, unseen data) |
| 3x attack class weight multiplier | Zero-Trust philosophy: better to false alarm than miss an attack |
| 15 trials per attack type | Provides enough variance to prevent LSTM sequence overfitting |
| 1km long haul normal flight | Teaches AI that long-distance missions are safe, not attacks |
| Dynamic speed variance (3-15 m/s) | Prevents AI from associating speed changes with attacks |
| Attack stage randomization | Prevents AI from associating attacks only with specific flight phases |

---

## 5. PROJECT FILE STRUCTURE

```
FYP PROJECT/
├── feature_extractor.py      # 26-feature vector engine
├── auto_generate_dataset.py  # Automated SITL dataset generator
├── train_models.py           # Bidirectional LSTM + SMOTE trainer
├── live_bridge.py            # Real-time AI telemetry bridge (Phase 4)
├── desktop_app.py            # PyQt5 monitoring dashboard (Phase 5)
├── simulate_attack.py        # Manual attack injection scripts
├── log_telemetry.py          # Raw telemetry logger
├── combine_data.py           # Dataset merger utility
├── perfect_dataset_v2.csv    # 41,199-row production dataset
├── lstm_uav_v2.h5            # Trained AI model (after Phase 3)
├── scaler_v2.pkl             # StandardScaler for live inference
├── README.md                 # Project documentation
└── RUN_GUIDE.md              # Setup and execution instructions
```

---

## 6. WORKFLOW TIMELINE

| Date | Phase | Work Done |
|------|-------|-----------|
| Apr 25 | Setup | Initial project setup, ArduPilot SITL installation |
| Apr 29 | v1 | First 19-feature model, basic dataset, initial dashboard |
| Apr 30 | Debug | Fixed UI freezing, threading issues, telemetry crashes |
| May 01 | Plan | Created formal implementation plan for thesis proposal |
| May 04 | Phase 1 | Built 26-feature extractor, removed flight_mode |
| May 04 | Phase 2 | Rewrote dataset generator, fixed GPS lock bug, fixed thread stealing, added 1km flight, generated 41,199-row dataset |
| May 05 | Phase 3 | Rewrote training script with Bidirectional LSTM, SMOTE, class weights |
| TBD | Phase 4 | Zero-Trust bridge with autonomous RTL lockdown |
| TBD | Phase 5 | Dashboard with threat alerts and auto-return mapping |

---

## 7. UNIQUE RESEARCH CONTRIBUTIONS

1. **Physics-Only Detection:** No reliance on network signatures or flight mode metadata. The AI detects attacks purely from how the drone physically moves.
2. **Hardware-Level Feature Fusion:** Combining RC channel raw values with motor servo outputs gives the AI direct visibility into whether the hardware is being externally manipulated.
3. **Delta-Rate Engineering:** Features like `gps_jump_magnitude` and `alt_trend_5tick` allow instant detection of sudden physical anomalies without waiting for sustained patterns.
4. **Zero-Trust Autonomous Mitigation:** The drone doesn't just detect the attack — it autonomously severs communication, locks out the attacker, and flies home.
5. **Multi-Stage Attack Simulation:** Attacks are triggered during different flight phases (hover, cruise, climb, long-haul), creating a robust training dataset that generalizes to real-world scenarios.

---

*This document serves as the complete technical diary and thesis reference for the UAV Cyber-Physical Intrusion Detection System project.*
