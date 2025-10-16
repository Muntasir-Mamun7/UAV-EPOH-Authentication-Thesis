import airsim
import socket
import json
import time 
import hashlib
import sys


UAV_SUPI = 'UAV_A1'           # Subscriber Identity (ID)
LONG_TERM_KEY = 'K_LongTerm_A1' # Long-Term Symmetric Key (K)
GCS_HOST = '127.0.0.1'        
GCS_PORT = 50001

AIRSIM_HOST_IP = "10.163.164.35" 
# ----------------------------------------------------

# --- Core Cryptographic and Telemetry Functions ---

def calculate_session_key_simulated(long_term_key, rand):
    """Simulates the derivation of the Session Key (KTx). KTx = HASH(K | RAND)"""
    combined = (long_term_key + str(rand)).encode('utf-8')
    return hashlib.sha256(combined).hexdigest()[:16]

def calculate_res_star_simulated(long_term_key, rand):
    """Simulates the UAV calculating its response (RES*)."""
    xres_data = (long_term_key + str(rand) + 'Expected').encode('utf-8')
    return hashlib.sha256(xres_data).hexdigest()[:10]

def get_telemetry_data(client):
    """Fetches key telemetry data from AirSim (position, altitude, velocity)."""
    state = client.getMultirotorState()
    pos = state.kinematics_estimated.position
    vel = state.kinematics_estimated.linear_velocity
    
    telemetry = {
        'x_pos': round(pos.x_val, 3),
        'y_pos': round(pos.y_val, 3),
        'z_alt': round(pos.z_val, 3), 
        'vel_mag': round((vel.x_val**2 + vel.y_val**2 + vel.z_val**2)**0.5, 3)
    }
    return telemetry

# --- Main Client Logic ---

def run_uav_client():
    airsim_client = None
    gcs_socket = None
    session_key = None
    
    print("--- STARTING UAV CLIENT EXECUTION ---")

    # --- 1. AirSim Setup and Takeoff ---
    try:
        airsim_client = airsim.MultirotorClient(ip=AIRSIM_HOST_IP)
        airsim_client.confirmConnection()
        print("✅ AirSim API Connection Confirmed.")
        
        print("Awaiting full PX4 link (3s delay)...")
        time.sleep(3) 
        
        airsim_client.enableApiControl(True)
        airsim_client.armDisarm(True)
        
        # Takeoff to 10 meters (-10 in NED)
        airsim_client.takeoffAsync(timeout_sec=5).join()
        airsim_client.moveToZAsync(-10, 5).join()
        print("✅ UAV Armed and Took Off to 10m altitude.")
        
    except Exception as e:
        print(f"❌ AirSim/PX4 Error: Failed to arm/take off. Details: {e}")
        return

    # --- 2. GCS Connection and Authentication ---
    try:
        gcs_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        gcs_socket.connect((GCS_HOST, GCS_PORT))
        print(f"✅ Connected to GCS Leader Node at {GCS_HOST}:{GCS_PORT}")
        
        # Authentication Logic (Simplified: Handshake occurs here)
        auth_request_1 = { 'type': 'AUTH_REQUEST_1', 'uav_supi': UAV_SUPI }
        gcs_socket.sendall(json.dumps(auth_request_1).encode('utf-8'))
        response_1 = json.loads(gcs_socket.recv(4096).decode('utf-8'))
        
        if response_1.get('status') == 'CHALLENGE_ISSUED':
            rand = response_1['rand']
            calculated_ktx = calculate_session_key_simulated(LONG_TERM_KEY, rand)
            calculated_res_star = calculate_res_star_simulated(LONG_TERM_KEY, rand)

            auth_response_2 = {
                'type': 'AUTH_RESPONSE_2', 'uav_supi': UAV_SUPI, 'res_star': calculated_res_star 
            }
            gcs_socket.sendall(json.dumps(auth_response_2).encode('utf-8'))
            response_2 = json.loads(gcs_socket.recv(4096).decode('utf-8'))
            
            if response_2.get('status') == 'AUTH_SUCCESS':
                session_key = response_2['session_key']
                print(f"✅ Mutual Authentication SUCCESS. Session Key established.")
            else:
                print(f"❌ AUTH FAILED. Reason: {response_2.get('reason', 'Unknown error')}")
        
    except Exception as e:
        print(f"❌ GCS Connection/Authentication Error: {e}")
    
    
    # --- 3. Telemetry Transmission (60-SECOND GUARANTEED FLIGHT) ---
    if session_key:
        print("\n--- Starting Authenticated Telemetry Logging (60 seconds) ---")
        
        # Define Path and Timing
        PATH_SEGMENTS = [
            (10, 0, -10),    # Hover 1: 10m East
            (10, 10, -10),   # Corner 1: 10m East, 10m North
            (0, 10, -10),    # Corner 2: 0m East, 10m North
            (0, 0, -10)      # Hover 2: Back to start X/Y
        ]
        TOTAL_FLIGHT_TIME = 60 # seconds
        LOG_INTERVAL = 2.0     # log every 2 seconds
        
        start_time = time.time()
        path_index = 0
        
        while time.time() - start_time < TOTAL_FLIGHT_TIME:
            
            # Select next waypoint in the loop
            wp_x, wp_y, wp_z = PATH_SEGMENTS[path_index % len(PATH_SEGMENTS)]
            path_index += 1
            
            # Command the drone to move (non-blocking call)
            airsim_client.moveToPositionAsync(wp_x, wp_y, wp_z, 5, timeout_sec=1).join()
            
            # Log Data multiple times while moving/hovering
            for i in range(2): 
                if time.time() - start_time >= TOTAL_FLIGHT_TIME:
                    break
                
                telemetry_data = get_telemetry_data(airsim_client)
                
                telemetry_tx = {
                    'type': 'TELEMETRY_TX', 'uav_supi': UAV_SUPI,
                    'session_key': session_key, 'data': telemetry_data
                }
                
                gcs_socket.sendall(json.dumps(telemetry_tx).encode('utf-8'))
                
                # Receive GCS acknowledgement
                response_tx = json.loads(gcs_socket.recv(4096).decode('utf-8'))
                
                if response_tx.get('status') == 'TX_BLOCK_ACK':
                    print(f"⬆️ TX ACK: Mined to Block! Hash: {response_tx['hash']}")
                else:
                    print(f"-> TX Sent. Waiting for block...")
                
                time.sleep(LOG_INTERVAL)

    # --- 4. Cleanup and Landing ---
    if airsim_client and session_key:
        print("\nLanding UAV and terminating session...")
        try:
            # 🚨 FIX A: Explicit landing command
            landing_task = airsim_client.landAsync()
            landing_task.join()  # Wait for the landing task to finish

            # 🚨 FIX B: Log a definitive "LANDING" transaction to the chain
            final_telemetry = get_telemetry_data(airsim_client)
            final_telemetry['status'] = 'LANDING_FINAL' # Custom status for final log
            
            final_tx = {
                'type': 'TELEMETRY_TX', 'uav_supi': UAV_SUPI,
                'session_key': session_key, 'data': final_telemetry
            }
            gcs_socket.sendall(json.dumps(final_tx).encode('utf-8'))
            
            # Wait for GCS to process the final block
            time.sleep(4) 
            
            airsim_client.armDisarm(False)
            airsim_client.reset()
            airsim_client.enableApiControl(False)
            
        except Exception as e:
            print(f"Warning: Cleanup/Landing failed. Drone may remain in air. Details: {e}")
            
    if gcs_socket:
        gcs_socket.close()
        
    print("\nUAV Client finished.")


if __name__ == '__main__':
    run_uav_client()