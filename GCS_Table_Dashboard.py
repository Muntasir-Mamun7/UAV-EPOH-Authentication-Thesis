import airsim
import cv2 # OpenCV
from PIL import Image, ImageTk # Pillow for Tkinter image handling

# Add this global variable for the AirSim connection details (must match UAV_Client.py)
AIRSIM_HOST_IP = "10.163.163.39" 
AIRSIM_PORT = 41451 # Default AirSim RPC Port

# GCS_Table_Dashboard.py - Simplified Text/Table Visualization for EPOH Thesis
import tkinter as tk
from tkinter import scrolledtext
import json
import time
import datetime
import os

LEDGER_FILE = 'epoh_ledger.json'

class GCSDashboard:
    def __init__(self, master):
        self.master = master
        master.title("EPOH UAV Data Log Dashboard")
        self.last_chain_length = 0

        # --- Status and Integrity Frame ---
        status_frame = tk.Frame(master)
        status_frame.pack(pady=10)

        self.status_label = tk.Label(status_frame, text="Status: Starting...", font=('Arial', 14, 'bold'))
        self.status_label.pack()

        self.hash_label = tk.Label(status_frame, text="Integrity Hash: N/A", font=('Courier', 10))
        self.hash_label.pack()

        # --- Data Log Scrolled Text Area ---
        self.log_area = scrolledtext.ScrolledText(master, width=110, height=30, font=('Courier', 10))
        self.log_area.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.initialize_log_header()

        # Start the update loop
        self.master.after(100, self.update_dashboard)

    def initialize_log_header(self):
        """Sets the initial header for the log area."""
        header = (
            "--- EPOH SECURE FLIGHT LOG ---\n"
            "Idx | Time Stamp | Event Tag | Path Coordinates (X, Y) | Altitude (Z) | Speed (m/s) | Auth Details\n"
            "------------------------------------------------------------------------------------------------------------\n"
        )
        self.log_area.delete(1.0, tk.END)
        self.log_area.insert(tk.END, header)

    def format_log_entry(self, block_index, tx_time, tx, chain_length):
        """Formats a single transaction for display, prioritizing telemetry."""
        dt_object = datetime.datetime.fromtimestamp(tx_time)
        data = tx.get('data', {}) 
        
        tag = "TX"
        detail_status = ""
        
        # --- Authentication/System Data Check ---
        if tx.get('status') == "AUTHENTICATED":
            tag = "AUTH"
            detail_status = f"AUTH OK | Key: {tx.get('session_key_sim', 'N/A')[:16]}..."
            
        elif tx.get('tx_id') == "GENESIS_TX":
            tag = "INIT"
            detail_status = "System Initialized"

       # --- TELEMETRY/PATH DATA CHECK ---
        elif 'x_pos' in data and 'y_pos' in data:
            x, y, z = data['x_pos'], data['y_pos'], data['z_alt']
            vel = data['vel_mag']
            
            # Check for the definitive LANDING status added in the client script
            event_tag = "PATH"
            if data.get('status') == "LANDING_FINAL":
                 event_tag = "LANDING"
            elif z < -0.5 and block_index == 3:
                 event_tag = "TAKEOFF"
            
            tag = event_tag
            
            detail_status = (
                f"({x:7.2f}, {y:7.2f}) | {z:6.2f}m     | {vel:5.2f} m/s   | N/A"
            )
            
        else:
            # Fallback for unhandled/general data
            tag = "MISC"
            detail_status = f"Raw TX ID: {tx.get('tx_id', 'N/A')}"
            
        # Format the line for the ScrolledText widget
        log_line = (
            f"[{block_index:>2}] {dt_object.strftime('%H:%M:%S.%f')[:-3]} | "
            f"{tag:<9} | {detail_status}\n"
        )
        return log_line

    def update_dashboard(self):
        """Reads the ledger and updates the text area."""
        try:
            with open(LEDGER_FILE, 'r') as f:
                chain = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.status_label.config(text="Status: Waiting for Chain...", fg="orange")
            self.master.after(1000, self.update_dashboard)
            return

        # --- Only append new data if the chain has grown ---
        if len(chain) > self.last_chain_length:
            
            # --- Append new blocks since the last update ---
            for block in chain[self.last_chain_length:]:
                
                # Process each transaction in the new block
                for tx in block['transactions']:
                    # Pass the current length of the chain for heuristic checks (like LANDING)
                    line = self.format_log_entry(block['index'], block['timestamp'], tx, len(chain))
                    self.log_area.insert(tk.END, line)

            # Scroll to the bottom and update last_chain_length
            self.log_area.see(tk.END)
            self.last_chain_length = len(chain)

        # --- Update status panel (Always update regardless of new block) ---
        last_block = chain[-1]
        is_authenticated = any(tx.get('status') == "AUTHENTICATED" for block in chain for tx in block.get('transactions', []))

        self.status_label.config(text=f"Status: {'✅ AUTHENTICATED (Log Live)' if is_authenticated else '⚠️ AWAITING AUTHENTICATION'}", 
                                fg="green" if is_authenticated else "red")
                                
        self.hash_label.config(text=f"Integrity Hash (Block {last_block['index']}): {last_block['current_hash']}")

        # Schedule the next update
        self.master.after(1000, self.update_dashboard)

if __name__ == '__main__':
    # Ensure the environment can find tkinter before starting
    try:
        root = tk.Tk()
    except Exception as e:
        print("FATAL ERROR: Failed to start Tkinter. Ensure 'sudo apt install python3-tk' was successful.")
        print(f"Details: {e}")
        sys.exit(1)
        
    app = GCSDashboard(root)
    root.mainloop()