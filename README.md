# 🛡️ EPOH UAV Authentication System
Decentralized and Verifiable Flight Data Logging
This project implements a lightweight, blockchain-based authentication and logging system for Unmanned Aerial Vehicles (UAVs). It utilizes a custom Proof-of-History Lite (EPOH) consensus mechanism to ensure high throughput, low latency, and irrefutable data integrity, making it ideal for resource-constrained aerial networks.

The system is demonstrated using a Software-in-the-Loop (SITL) simulation integrating AirSim (Unreal Engine) and the PX4 Flight Stack.
## 🔑 Core Features & Solution
This project solves the critical problem of Non-Repudiation in drone operations by making all flight logs cryptographically tamper-proof.

That's the final, crucial step! Having a professional README.md file is essential for your GitHub repository. It serves as the project's introduction and guide.

Based on the file structure you uploaded (confirming all Python scripts and data files are present) and the core concepts of your thesis, here is a complete and impressive README.md template you can use.

Action: Create and Populate the README.md File
Go to your GitHub Repository in your browser.

Click the "Add a README" button (or create a new file named README.md).

Paste the content below, then commit the new file directly.

README.md Template
🛡️ EPOH UAV Authentication System (Undergraduate Thesis)
Decentralized and Verifiable Flight Data Logging
This project implements a lightweight, blockchain-based authentication and logging system for Unmanned Aerial Vehicles (UAVs). It utilizes a custom Proof-of-History Lite (EPOH) consensus mechanism to ensure high throughput, low latency, and irrefutable data integrity, making it ideal for resource-constrained aerial networks.

The system is demonstrated using a Software-in-the-Loop (SITL) simulation integrating AirSim (Unreal Engine) and the PX4 Flight Stack.

🔑 Core Features & Solution
This project solves the critical problem of Non-Repudiation in drone operations by making all flight logs cryptographically tamper-proof.

Feature	Technical Implementation	Thesis Proof
Authentication	Mutual Challenge-Response Protocol (ECC Simulation) between the UAV and the GCS Leader Node.	Grants control only to authenticated devices and establishes a secure session key (K 
Tx
​
 ).
Data Integrity	Proof-of-History Lite (EPOH) consensus based on sequential hashing.	Creates a verified, chronological timeline of telemetry data. Tampering with any log entry breaks the hash chain (demonstrated by verify_chain.py).
Performance	EPOH eliminates computationally expensive proof-of-work (PoW), allowing the system to log high-frequency telemetry data efficiently.	Latency is reduced, enabling real-time operation crucial for drone swarms.
Unified Monitoring	Tkinter/OpenCV Dashboard	Combines the live drone camera feed with the authenticated, real-time data log in a single GUI.
🛠️ Project Structure and Components
The repository contains all necessary components to run the full simulation:

UAV_Client.py: The main execution script. It handles the UAV's flight commands (Takeoff → Path → Landing), executes the authentication protocol, and streams telemetry data to the GCS Leader Node.

GCS_LeaderNode.py: The Blockchain Server. It manages the state, validates authentication responses, and runs the EPOH sequential hashing algorithm to mine blocks and write the immutable log.

epoh_core.py: Contains the core logic for cryptographic hashing and the EPOH block structure.

GCS_Combined_Dashboard.py: The final unified UI. Reads the epoh_ledger.json file in real-time, displaying the secured flight coordinates and the live authentication status.

verify_chain.py: The crucial audit tool. Loads the final ledger and checks every single hash link for integrity and chronological order.

settings.json: AirSim configuration file (tuned for PX4 SITL and cross-network communication via WSL).

epoh_ledger.json: The final, authenticated flight data log (the immutable ledger).

🚀 How to Run the Simulation
The system requires three simultaneous terminal processes running inside a WSL Ubuntu environment, connected to the AirSim/Unreal Engine application running on Windows.

Prerequisites
AirSim/Unreal Engine: City Park Environment must be running on Windows.

PX4 SITL: PX4 must be built and running in WSL.

Python Libraries: pip install airsim opencv-python Pillow numpy

Tkinter: sudo apt install python3-tk

Execution Order
1. Terminal 1 (WSL - PX4 Flight Controller)
cd px4v1.15.2
make px4_sitl_default none_iris
2. Terminal 2 (WSL - GCS Leader Node / BLOCKCHAIN SERVER)
python3 GCS_LeaderNode.py
3. Terminal 3 (WSL - UAV Client / FLIGHT EXECUTION)
python3 UAV_Client.py
4.Terminal 4 (WSL - GCS Dashboard / VISUALIZATION)
python3 GCS_Combined_Dashboard.py


Developed by MUNTASIR AL MAMUN for Undergraduate Thesis Institution: Nanjing University of Posts and Telecommunications
