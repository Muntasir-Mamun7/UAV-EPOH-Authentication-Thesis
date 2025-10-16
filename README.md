# 🛡️ EPOH UAV Authentication System
Decentralized and Verifiable Flight Data Logging
This project implements a lightweight, blockchain-based authentication and logging system for Unmanned Aerial Vehicles (UAVs). It utilizes a custom Proof-of-History Lite (EPOH) consensus mechanism to ensure high throughput, low latency, and irrefutable data integrity, making it ideal for resource-constrained aerial networks.

The system is demonstrated using a Software-in-the-Loop (SITL) simulation integrating AirSim (Unreal Engine) and the PX4 Flight Stack.
## 🔑 Core Features & Solution
This project solves the critical problem of Non-Repudiation in drone operations by making all flight logs cryptographically tamper-proof.

## 🛠️ Project Structure and Components
The repository contains all necessary components to run the full simulation:

UAV_Client.py: The main execution script. It handles the UAV's flight commands (Takeoff → Path → Landing), executes the authentication protocol, and streams telemetry data to the GCS Leader Node.

GCS_LeaderNode.py: The Blockchain Server. It manages the state, validates authentication responses, and runs the EPOH sequential hashing algorithm to mine blocks and write the immutable log.

epoh_core.py: Contains the core logic for cryptographic hashing and the EPOH block structure.

GCS_Combined_Dashboard.py: The final unified UI. Reads the epoh_ledger.json file in real-time, displaying the secured flight coordinates and the live authentication status.

verify_chain.py: The crucial audit tool. Loads the final ledger and checks every single hash link for integrity and chronological order.

settings.json: AirSim configuration file (tuned for PX4 SITL and cross-network communication via WSL).

epoh_ledger.json: The final, authenticated flight data log (the immutable ledger).

## 🚀 How to Run the Simulation
The system requires three simultaneous terminal processes running inside a WSL Ubuntu environment, connected to the AirSim/Unreal Engine application running on Windows.

### Prerequisites
AirSim/Unreal Engine: City Park Environment must be running on Windows.

PX4 SITL: PX4 must be built and running in WSL.

Python Libraries: pip install airsim opencv-python Pillow numpy

Tkinter: sudo apt install python3-tk

### Execution Order
#### 1. Terminal 1 (WSL - PX4 Flight Controller)
cd px4v1.15.2
make px4_sitl_default none_iris
#### 2. Terminal 2 (WSL - GCS Leader Node / BLOCKCHAIN SERVER)
python3 GCS_LeaderNode.py
#### 3. Terminal 3 (WSL - UAV Client / FLIGHT EXECUTION)
python3 UAV_Client.py
#### 4.Terminal 4 (WSL - GCS Dashboard / VISUALIZATION)
python3 GCS_Combined_Dashboard.py


Developed by MUNTASIR AL MAMUN for Undergraduate Thesis Institution: Nanjing University of Posts and Telecommunications
