# GCS_Combined_Dashboard.py - Final, Robust Single UI for Thesis Presentation
# Combines Live Image Feed (best effort stream) with Authenticated EPOH Log Table.

import tkinter as tk
from tkinter import scrolledtext
import json
import time
import datetime
import airsim
import cv2 
import numpy as np
from PIL import Image, ImageTk 
import sys
import os

# --- Configuration (MUST MATCH UAV_Client.py) ---
LEDGER_FILE = 'epoh_ledger.json'
# ENSURE THIS IS YOUR CURRENT WINDOWS HOST IP
AIRSIM_HOST_IP = "10.163.164.35" 
AIRSIM_PORT = 41451
IMAGE_DISPLAY_SIZE = (640, 360) 
# ----------------------------------------------------

class GCSCombinedDashboard:
    def __init__(self, master):
        self.master = master
        master.title("EPOH UAV AUTHENTICATION AND LIVE LOG")
        self.last_chain_length = 0
        self.tk_img = None
        
        # --- AirSim Client Setup ---
        try:
            self.airsim_client = airsim.MultirotorClient(ip=AIRSIM_HOST_IP, port=AIRSIM_PORT)
            self.airsim_client.confirmConnection()
        except Exception as e:
            self.airsim_client = None
            print(f"Live View Connection Error: Failed to connect to AirSim for status checks. Details: {e}") 

        # --- Top Frame for Image and Status ---
        top_frame = tk.Frame(master)
        top_frame.pack(pady=5, padx=5, fill=tk.X)

        # 1. Image Display (Left)
        image_container = tk.Frame(top_frame)
        image_container.pack(side=tk.LEFT, padx=10)
        self.image_label = tk.Label(image_container, text="Live Drone View (Connecting...)")
        self.image_label.pack()
        
        # 2. Status Display (Right)
        status_container = tk.Frame(top_frame)
        status_container.pack(side=tk.RIGHT, fill=tk.Y, padx=10)

        self.status_label = tk.Label(status_container, text="Status: Starting...", font=('Arial', 14, 'bold'))
        self.status_label.pack(anchor='w', pady=5)
        
        self.hash_label = tk.Label(status_container, text="Integrity Hash: N/A", font=('Courier', 10))
        self.hash_label.pack(anchor='w')

        # --- Data Log Scrolled Text Area (Bottom) ---
        self.log_area = scrolledtext.ScrolledText(master, width=110, height=20, font=('Courier', 10))
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

    def load_static_image(self):
        """Placeholder function to show what a failed stream looks like, keeping the UI running."""
        self.image_label.config(text="Live View: Image stream currently UNAVAILABLE.", fg="red")
        
    def update_image(self):
        """Fetches and updates the drone camera image, with robust error handling."""
        if self.airsim_client:
            try:
                # 1. Request image data
                responses = self.airsim_client.simGetImages([airsim.ImageRequest("0", airsim.ImageType.Scene, False, False)])
                
                if not responses:
                    self.image_label.config(text="Live View: No response from camera API.", image=None)
                    return False
                
                img_data = responses[0].image_data_uint8
                
                # 2. CRITICAL CHECK: Ensure data is not empty before decoding
                if not img_data or len(img_data) == 0:
                    # Log an error but do not crash the application
                    self.image_label.config(text="Live View: Image stream returned empty frame.", image=None, fg="red")
                    return False

                # 3. Decode the image data 
                np_arr = np.frombuffer(img_data, np.uint8)
                img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR) 
                
                # 4. Final check before processing (fixes the OpenCV Assert error)
                if img_bgr is None or img_bgr.size == 0:
                    self.image_label.config(text="Live View: Decoding Failed (Invalid Data).", image=None, fg="red")
                    return False

                # 5. Process and Display
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(img_rgb)
                
                # Resize for display
                img_pil = img_pil.resize(IMAGE_DISPLAY_SIZE, Image.LANCZOS)
                
                # Convert to PhotoImage for Tkinter
                self.tk_img = ImageTk.PhotoImage(img_pil) 
                
                # Update the label
                self.image_label.config(image=self.tk_img, text="Live View: Streaming...", fg="blue")
                self.image_label.image = self.tk_img 
                return True
                
            except Exception as e:
                self.image_label.config(text=f"Live View Exception: {e}", image=None, fg="red")
        return False
    
    def format_log_entry(self, block_index, tx_time, tx, chain_length):
        """Formats a single transaction for display."""
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
            
            # Identify Takeoff/Landing heuristically 
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
            tag = "MISC"
            detail_status = f"Raw TX ID: {tx.get('tx_id', 'N/A')}"
            
        # Format the log line
        log_line = (
            f"[{block_index:>2}] {dt_object.strftime('%H:%M:%S.%f')[:-3]} | "
            f"{tag:<9} | {detail_status}\n"
        )
        return log_line

    def update_dashboard(self):
        """Main update loop that refreshes data and image."""
        
        # 1. Update Image (Best effort stream)
        self.update_image()
        
        # 2. Update Data Log
        try:
            with open(LEDGER_FILE, 'r') as f:
                chain = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.status_label.config(text="Status: Waiting for Chain...", fg="orange")
            self.master.after(500, self.update_dashboard)
            return

        if len(chain) > self.last_chain_length:
            # Append new blocks since the last update
            for block in chain[self.last_chain_length:]:
                for tx in block['transactions']:
                    line = self.format_log_entry(block['index'], block['timestamp'], tx, len(chain))
                    self.log_area.insert(tk.END, line)

            self.log_area.see(tk.END)
            self.last_chain_length = len(chain)

        # 3. Update status panel
        last_block = chain[-1]
        is_authenticated = any(tx.get('status') == "AUTHENTICATED" for block in chain for tx in block.get('transactions', []))

        self.status_label.config(text=f"Status: {'✅ AUTHENTICATED (Log Live)' if is_authenticated else '⚠️ AWAITING AUTHENTICATION'}", 
                                fg="green" if is_authenticated else "red")
                                
        self.hash_label.config(text=f"Integrity Hash (Block {last_block['index']}): {last_block['current_hash']}")

        # Schedule the next update
        self.master.after(500, self.update_dashboard)

if __name__ == '__main__':
    # Add necessary imports just for safety
    try:
        import numpy as np
        import cv2
        from PIL import Image, ImageTk 
    except ImportError as e:
        print(f"FATAL ERROR: Missing library ({e}). Please run 'pip install opencv-python Pillow numpy'.")
        sys.exit(1)
        
    try:
        root = tk.Tk()
    except Exception as e:
        print("FATAL ERROR: Failed to start Tkinter. Ensure 'sudo apt install python3-tk' was successful.")
        sys.exit(1)
        
    app = GCSCombinedDashboard(root)
    root.mainloop()