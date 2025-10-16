# GCS_Dashboard.py - Runs the simple visualization (Tkinter + Matplotlib)
# This script reads the epoh_ledger.json file in real-time and updates the GUI.

import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json
import time

LEDGER_FILE = 'epoh_ledger.json'

def update_dashboard(canvas, ax_path, ax_alt, status_label, hash_label):
    """Reads the ledger and updates all visualization elements."""
    try:
        # Load the latest state of the immutable ledger
        with open(LEDGER_FILE, 'r') as f:
            chain = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Handle case where the file hasn't been created yet or is corrupted
        status_label.config(text="Status: Waiting for Chain...", fg="orange")
        # Schedule the next check
        root.after(1000, lambda: update_dashboard(canvas, ax_path, ax_alt, status_label, hash_label))
        return

    # --- Data Filtering ---
    telemetry_blocks = [b for b in chain if b.get('index', 0) >= 3]
    
    x_coords, y_coords, altitudes, speeds, indices = [], [], [], [], []
    is_authenticated = False
    
    for block in telemetry_blocks:
        # Check for the Authentication Success Block
        if block.get('index') == 2:
            is_authenticated = True
        
        for tx in block.get('transactions', []):
            if tx.get('data'): # It's a telemetry transaction
                data = tx['data']
                x_coords.append(data['x_pos'])
                y_coords.append(data['y_pos'])
                altitudes.append(data['z_alt'])
                speeds.append(data['vel_mag'])
                indices.append(block['index'])

    # --- Update Status Labels (Top Panel) ---
    if is_authenticated:
        # Extract the secure session key from the AUTH_SUCCESS block
        auth_tx = [tx for block in chain for tx in block.get('transactions', []) if tx.get('status') == 'AUTHENTICATED']
        key = auth_tx[0]['session_key_sim'] if auth_tx else 'N/A'
        status_label.config(text=f"Status: ✅ AUTHENTICATED (Session Key: {key[:8]}...)", fg="green")
    else:
        status_label.config(text="Status: ⚠️ AWAITING AUTHENTICATION", fg="red")
        
    last_hash = chain[-1]['current_hash']
    hash_label.config(text=f"Integrity Hash (Block {chain[-1]['index']}): {last_hash}", fg="blue")


    # --- Update Plots ---
    
    # 1. Path Visualization (X-Y)
    ax_path.clear()
    if x_coords:
        # Plot path with a smooth blue line for clarity
        ax_path.plot(x_coords, y_coords, linestyle='-', color='blue', label='Flight Path') 
        # Highlight current position
        ax_path.scatter(x_coords[-1], y_coords[-1], color='red', s=50, label=f'Current UAV Pos: ({x_coords[-1]:.1f}, {y_coords[-1]:.1f})')
        
        # Add lines to indicate the takeoff point (0,0)
        ax_path.axhline(0, color='gray', linestyle='--', linewidth=0.5)
        ax_path.axvline(0, color='gray', linestyle='--', linewidth=0.5)
        
    ax_path.set_title("UAV Flight Path (X vs Y)")
    ax_path.set_xlabel("X Position (meters)")
    ax_path.set_ylabel("Y Position (meters)")
    ax_path.legend(loc='upper left')
    ax_path.grid(True)
    
    # 2. Altitude and Velocity Chart
    ax_alt.clear()
    
    if indices:
        # Altitude plot (Primary Y-axis)
        ax_alt.plot(indices, altitudes, label='Altitude (Z-Alt)', color='green')
        ax_alt.set_title("Altitude and Velocity Over Time")
        ax_alt.set_xlabel("Block Index (EPOH Timeline)")
        ax_alt.set_ylabel("Altitude (m)", color='green')
        ax_alt.tick_params(axis='y', labelcolor='green')

        # Velocity plot (Secondary Y-axis)
        ax_speed = ax_alt.twinx()
        ax_speed.plot(indices, speeds, label='Velocity (m/s)', color='red')
        ax_speed.set_ylabel("Velocity (m/s)", color='red')
        ax_speed.tick_params(axis='y', labelcolor='red')
    else:
        ax_alt.set_title("Waiting for Telemetry Data...")

    # Adjust layout to prevent labels from overlapping
    fig.tight_layout() 

    canvas.draw()
    
    # Schedule the next update in 1000ms (1 second)
    root.after(1000, lambda: update_dashboard(canvas, ax_path, ax_alt, status_label, hash_label))

# --- Main Tkinter Setup ---
root = tk.Tk()
root.title("EPOH UAV Authentication Dashboard")

# Frame for Status Labels
status_frame = tk.Frame(root)
status_frame.pack(pady=10)

status_label = tk.Label(status_frame, text="Status: Starting...", font=('Arial', 14, 'bold'))
status_label.pack()

hash_label = tk.Label(status_frame, text="Latest Hash: N/A", font=('Courier', 10))
hash_label.pack()

# Matplotlib Figure (Container for plots)
fig = Figure(figsize=(10, 7), dpi=100)
ax_path = fig.add_subplot(211) # 2 rows, 1 column, 1st plot
ax_alt = fig.add_subplot(212) # 2 rows, 1 column, 2nd plot

# Matplotlib Canvas (Embeds the figure into the Tkinter window)
canvas = FigureCanvasTkAgg(fig, master=root)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(fill=tk.BOTH, expand=True)


# Start the update loop
root.after(100, lambda: update_dashboard(canvas, ax_path, ax_alt, status_label, hash_label))

root.mainloop()