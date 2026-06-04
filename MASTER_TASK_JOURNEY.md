# The Master Task Journey: UAV Cyber Defense System

This document contains every single task from the absolute beginning of the project to the final goal. It shows everything we have accomplished and everything we have left to do, in perfect chronological order.

---

## ✅ PHASE 0: Environment Setup (COMPLETED)
- [x] Install ArduPilot SITL simulator.
- [x] Configure `udp:127.0.0.1:14550` connection.
- [x] Verify basic MAVLink communication (`pymavlink`).
- [x] Install initial Python libraries (`pandas`, `numpy`, `tensorflow`, `PyQt5`).

---

## ❌ ITERATION 1: The "V1" Legacy Architecture (DEPRECATED & ABANDONED)
*In research, the first attempt reveals what needs to be fixed. Here are the tasks we completed early on, and exactly why we threw them away.*
- [x] **V1 Dataset Generation (`perfect_dataset.csv`):** 
  - *Why we abandoned it:* It was too basic. The flight paths were too short, the speeds lacked variance, and critically, it included `flight_mode` as a feature. This caused the AI to trigger a false alarm every time the human operator manually changed modes.
- [x] **V1 Model Training (`lstm_uav_model.h5`):**
  - *Why we abandoned it:* It was trained on the flawed V1 dataset. It only used 19 features and a 10-tick (1-second) memory window. We discovered 1 second is not long enough to confidently detect gradual cyber attacks like GPS Spoofing.
- [x] **V1 Web Dashboard (`live_bridge.py` & Flask):**
  - *Why we abandoned it:* We originally built a Flask web server and used SocketIO to stream data. We abandoned this because web sockets introduce network latency, and in a zero-trust cyber defense system, every millisecond counts. 
- [x] **The SITL Grounding Bug:**
  - *What happened:* During V1, the drone refused to take off. 
  - *Why it happened:* The telemetry logger was violently pulling MAVLink data on a blocking thread, which starved the Commander thread and blocked the `ARM` command. 
  - *The Fix:* We had to completely redesign the system to use a non-blocking `state_dict` shared memory architecture.

---

## ✅ ITERATION 2: Transitioning to the 5-Class Threat System (THE MISSING LINK)
*Before we perfected the 26 features, we had to upgrade the core architecture from a simple binary system (Normal vs Attack) to a specific 5-Class Threat System. These were the core tasks we accomplished to make that jump:*

- [x] **Phase 1: Automated Dataset Generator Upgrade**
  - [x] Create `auto_generate_dataset.py` from scratch.
  - [x] Implement MAVLink automated flight sequences (Takeoff, cruise, land).
  - [x] Implement automated attack injection synced with labels 1-4.
  - [x] Ensure output is formatted exactly like the old `combined_dataset.csv`.
- [x] **Phase 2: Upgrading the AI Brain**
  - [x] Modify `train_models.py` architecture (changing the final layer to `Dense(5, softmax)`).
  - [x] Update loss function from binary to `sparse_categorical_crossentropy`.
  - [x] Update class weights calculation to handle all 5 distinct classes.
- [x] **Phase 3: Smart Mitigation & UI**
  - [x] Modify `desktop_app.py` AI inference loop to handle the 5 output classes.
  - [x] Update UI Banner text to display the *specific* threats rather than a generic warning.
  - [x] Rewrite `trigger_mitigation()` to execute specific defense protocols based on the exact attack detected.
- [x] **Phase 4: Execution**
  - [x] User runs data generator (wait 15 mins).
  - [x] Train new 5-class model.
  - [x] Validate live dashboard compatibility.

---

## ✅ PHASE 1: Feature Engineering V2 (COMPLETED)
- [x] Create `feature_extractor.py`.
- [x] ⚠ **CRITICAL:** Remove `flight_mode` from the features so the AI relies purely on physics, preventing false alarms on manual operator commands.
- [x] Extract 14 core physics features (alt, speed, pitch, roll, yaw, climb, etc.).
- [x] Extract 2 RC hardware features (`ch1_roll_raw`, `ch3_throttle_raw`) to detect RC Hijacks.
- [x] Extract 3 motor/armed features (`armed_state`, `servo1_out`, `servo3_out`) to detect mid-air disarms.
- [x] Compute 4 Delta/Rate features (`alt_delta`, `alt_trend`, `speed_delta`, `vz`) to detect Mode Forcing.
- [x] Compute 3 GPS Jump features (`gps_lat_delta`, `gps_lon_delta`, `gps_jump_magnitude`) to detect GPS Spoofing.
- [x] Verify the exact 26-feature output vector.

## ✅ PHASE 2: Perfect Dataset Generation (COMPLETED)
- [x] Update `auto_generate_dataset.py` to use the 26-feature extractor.
- [x] Implement `wait_for_gps_lock()` and strict arming loops so the drone doesn't crash on takeoff.
- [x] Fix Thread-Stealing bug between Logger and Commander using `state_dict`.
- [x] **Normal Flight:** Fly for 10 minutes. Include a massive **1-Kilometer Long Haul** flight to teach the AI what safe long-distance flight looks like. Vary speeds (3-15 m/s).
- [x] **RC Hijack Attack:** 15 trials (10-30s). Vary active channels.
- [x] **Mode Forcing Attack:** 15 trials (8-25s). Force malicious modes (LAND, RTL).
- [x] **GPS Spoofing Attack:** 15 trials (15-40s). Inject 3-9km offsets.
- [x] **Mid-Air Disarm Attack:** 15 trials. Corrupt `ARMING_CHECK` parameter and force motor kill.
- [x] Trigger attacks randomly across different flight stages (Hovering vs Cruising vs 1km Long Haul).
- [x] Successfully generate `perfect_dataset_v2.csv` (Result: 41,199 rows of perfect data!).

## ✅ PHASE 3: Deep Learning Training (COMPLETED)
- [x] Rewrite `train_models.py` for the 26-feature vector.
- [x] Install `imbalanced-learn`.
- [x] Format data into 50-tick (5-second) 3D sequences.
- [x] Ensure `train_test_split` happens *before* SMOTE to prevent data leakage cheating.
- [x] Apply `SMOTE` to perfectly balance the rare attack classes.
- [x] Compute Zero-Trust `class_weights` (Applying a 3x penalty to force the AI to be extremely sensitive to attacks).
- [x] Build the `Bidirectional(LSTM)` architecture with Dropout and BatchNormalization.
- [x] Train the AI on the 41,000 rows.
- [x] Evaluate the Confusion Matrix (Achieved 100% Recall on Attacks!).
- [x] Export `lstm_uav_v2.h5` (The Brain) and `scaler_v2.pkl` (The Translator).

## 🔲 PHASE 4: Zero-Trust Telemetry Bridge (UP NEXT)
**Note:** We executed an *Architectural Pivot*. We are abandoning the standalone `live_bridge.py` script because it causes latency. We are building the bridge directly into the dashboard (`desktop_app.py`).
- [ ] Rewrite the `UAVDataBridge` class inside `desktop_app.py`.
- [ ] Load the new `lstm_uav_v2.h5` and `scaler_v2.pkl`.
- [ ] Change the rolling window memory from 10 ticks to 50 ticks (5 seconds).
- [ ] Plug in the new `feature_extractor.py` to feed the 26 features into the model live.
- [ ] Implement the 3-tick consensus logic (AI must detect the attack 3 times in a row before triggering).
- [ ] **Zero-Trust Lockdown Protocol:**
  - When attack is confirmed, instantly overrule all external RC inputs.
  - Autonomously force the drone into `RTL` (Return to Launch) mode.
  - Ignore the command center controls until the drone lands safely.

## 🔲 PHASE 5: GUI Dashboard Rebuild (PyQt5 Migration)
- [ ] Rebuild dashboard using PyQt5 architecture for all 6 sidebar pages.
- [ ] See [PHASE5_UI_REBUILD_TASKS.md](file:///home/thigan/Desktop/FYP%20PROJECT/PHASE5_UI_REBUILD_TASKS.md) for the detailed step-by-step implementation plan including all functions, modules, and components.
- [ ] Perform the Final End-to-End Live Demonstration!

