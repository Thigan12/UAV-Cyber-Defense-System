# 🛡️ Autonomous UAV Cyber Defense & Command System

**MSc Final Year Project (FYP)**  
An advanced, AI-driven Intrusion Detection System (IDS) and Command & Control (C2) dashboard designed to detect cyberattacks on Unmanned Aerial Vehicles (UAVs) and execute autonomous Zero-Trust threat mitigation.

---

## 🚀 Key Features

* **Deep Learning Intrusion Detection:** Utilizes a custom-trained **LSTM (Long Short-Term Memory)** neural network to constantly analyze a 19-feature vector of MAVLink telemetry in real-time. Detects injection attacks, GPS spoofing, and unauthorized RC overrides with high accuracy.
* **Zero-Trust Threat Mitigation:** If the AI confidence threshold breaks 55%, the system immediately triggers a Zero-Trust protocol. It autonomously disables external RC overrides, locks manual flight controls, and forces the UAV into an emergency Return to Launch (RTL) mode to evade the threat zone.
* **Military-Grade C2 Dashboard:** Built with `CustomTkinter`, featuring a sleek, cyberpunk-inspired dark UI. Includes live telemetry tracking, an active Attack Probability Gauge, and real-time Matplotlib scrolling graphs utilizing fused EKF altitude data.
* **Interactive "Click-to-Fly":** Integrated `TkinterMapView` allows operators to right-click anywhere on the map to autonomously route the drone. Features dynamic auto-takeoff detection and intelligent altitude routing.
* **Granular Command Logging:** A side-by-side split terminal isolates raw MAVLink packet streams from a highly readable, timestamped Command & Alert Log that details exact autopilot operations, engine spool-ups, and threat evasions.

## 🛠️ Technology Stack
* **Autopilot & Simulation:** ArduPilot SITL, MAVLink, PyMavlink
* **Artificial Intelligence:** TensorFlow, Keras, Scikit-learn, Numpy
* **Desktop UI:** Python 3, CustomTkinter, TkinterMapView, PIL
* **Live Data Visualization:** Matplotlib, FigureCanvasTkAgg

## ⚙️ Architecture Workflow
1. `live_bridge.py` operates a background threading loop, intercepting `GPS_RAW_INT`, `ATTITUDE`, and `VFR_HUD` MAVLink streams.
2. The data is normalized via a pre-fitted scaler (`scaler.pkl`) and passed into the sliding window of the LSTM model (`lstm_uav_model.h5`).
3. If anomalous command injections are detected (via `simulate_attack.py`), the bridge fires an interrupt to `desktop_app.py`, changing the UI state to a Red Alert and initiating the MAVLink RTL override.

---
*Developed for MSc Final Year Project.*
