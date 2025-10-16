# GCS_LeaderNode.py - Runs the Leader Node, EPOH chain, and Authentication Server

import socket
import json
import time
import hashlib
import os

# --- Configuration ---
HOST = '127.0.0.1' 
PORT = 50001        
NODE_ID = 'Leader_Node_1'
LEDGER_FILE = 'epoh_ledger.json'

# Simulated Pre-Registered Database (UAV ID: Long-Term Key)
UAV_DB = {
    'UAV_A1': 'K_LongTerm_A1',  # UAV_A1's Long-Term Symmetric Key (K)
    'UAV_B2': 'K_LongTerm_B2'   # Example second UAV
}

# --- Import necessary core functions (requires epoh_core.py) ---

# We define these locally to ensure the script is self-contained for execution
def generate_key_pair_simulated():
    """Simulates ECC key pair generation."""
    return "NodePrivKey_Sim", "NodePubKey_Sim"

def calculate_session_key_simulated(long_term_key, rand):
    """Simulates the derivation of the Session Key (KTx). KTx = HASH(K | RAND)"""
    combined = (long_term_key + str(rand)).encode('utf-8')
    return hashlib.sha256(combined).hexdigest()[:16] # 16-char session key

def generate_auth_vector_simulated(uav_supi, long_term_key):
    """
    Simulates the server generating the Authentication Vector (AV).
    AV = (RAND, AUTN, XRES*, KTx)
    """
    rand = int(time.time() * 1000) # Unique Random Challenge
    
    # AUTN = HASH(K | SUPI | RAND) -> Authentication Token
    autn_data = (long_term_key + uav_supi + str(rand)).encode('utf-8')
    autn = hashlib.sha256(autn_data).hexdigest()
    
    # XRES* (Expected Response) -> Used for final verification
    xres_data = (long_term_key + str(rand) + 'Expected').encode('utf-8')
    xres_star = hashlib.sha256(xres_data).hexdigest()[:10]
    
    return rand, autn, xres_star, calculate_session_key_simulated(long_term_key, rand)

class EPOH_Core:
    """
    Implements the simplified Proof-of-History (PoH) function.
    """
    def __init__(self, difficulty=2):
        self.difficulty = difficulty 
        self.latest_hash = '0' * 64
        self.sequence_count = 0
        self.chain = [] # Store chain here for access by create_block

    def generate_sequential_hash(self):
        """Generates the next hash in the sequence."""
        data = self.latest_hash.encode('utf-8')
        new_hash = hashlib.sha256(data).hexdigest()
        self.latest_hash = new_hash
        self.sequence_count += 1
        return new_hash

    def embed_transaction(self, data_payload):
        """Incorporates transaction data into the sequential hash to timestamp it."""
        data_string = json.dumps(data_payload, sort_keys=True)
        combined_data = (self.latest_hash + data_string).encode('utf-8')
        
        self.latest_hash = hashlib.sha256(combined_data).hexdigest()
        self.sequence_count += 1
        
        return time.time(), self.latest_hash

    def create_block(self, transactions, previous_hash, current_chain_length):
        """
        Leader Node function: creates a new block containing a PoH-proof.
        """
        self.latest_hash = previous_hash
        self.sequence_count = 0
        
        event_log = []
        
        for tx in transactions:
            # Generate intermediate hashes (simulating time delay)
            for _ in range(self.difficulty):
                self.generate_sequential_hash()
            
            # Embed the transaction data (The EPOH step)
            tx_time, tx_hash = self.embed_transaction(tx)
            
            event_log.append({
                'event_type': 'TRANSACTION_EMBEDDED',
                'timestamp': tx_time,
                'hash_at_event': tx_hash,
                'tx_id': tx.get('tx_id')
            })

        # Finalize the Block
        final_block = {
            'index': current_chain_length + 1,
            'timestamp': time.time(),
            'previous_hash': previous_hash,
            'event_log': event_log, # The verifiable PoH timeline
            'transactions': transactions
        }
        
        # The block hash is based on the final PoH-linked state (latest_hash)
        final_block['current_hash'] = self.latest_hash 
        return final_block


# ---------------------

class LeaderNode:
    def __init__(self):
        self.chain = []
        self.transaction_pool = [] # For telemetry and successfully completed TXs
        self.pending_auth_challenges = {} # 🚨 CRITICAL FIX: Store AUTH challenges here separately
        self.epoh = EPOH_Core(difficulty=2) 
        self.load_chain()
        if not self.chain:
            self.create_genesis_block()

    def load_chain(self):
        """Loads the chain from the JSON file if it exists."""
        try:
            if os.path.exists(LEDGER_FILE):
                with open(LEDGER_FILE, 'r') as f:
                    self.chain = json.load(f)
                self.epoh.latest_hash = self.chain[-1]['current_hash']
                print(f"Loaded chain with {len(self.chain)} blocks.")
            else:
                self.chain = []
        except (json.JSONDecodeError, IndexError):
             print(f"Error loading {LEDGER_FILE}. Starting new chain.")
             self.chain = []


    def save_chain(self):
        """Saves the current chain state to the JSON file."""
        with open(LEDGER_FILE, 'w') as f:
            json.dump(self.chain, f, indent=4)

    def create_genesis_block(self):
        """Creates the first block in the chain."""
        genesis_block = {
            'index': 0, 
            'timestamp': time.time(), 
            'previous_hash': '0',
            'event_log': [{'event_type': 'CHAIN_START'}],
            'transactions': [{'tx_id': 'GENESIS_TX', 'data': 'System Initialized'}]
        }
        # Use the EPOH core to finalize the genesis hash
        self.epoh.latest_hash = self.epoh.generate_sequential_hash()
        genesis_block['current_hash'] = self.epoh.latest_hash
        
        self.chain.append(genesis_block)
        self.save_chain()
        print(f"Genesis Block Created. Hash: {genesis_block['current_hash'][:10]}...")

    def handle_uav_request(self, conn, request):
        """Handles both Authentication Requests and Telemetry Transactions."""
        request_type = request.get('type')
        uav_supi = request.get('uav_supi')
        
        if uav_supi not in UAV_DB:
            return {'status': 'AUTH_FAILURE', 'reason': 'Unknown SUPI/UAV ID'}
            
        long_term_key = UAV_DB[uav_supi]

        if request_type == 'AUTH_REQUEST_1':
            # --- AUTH STEP 1: Generate Authentication Vector (AV) ---
            rand, autn, xres_star, ktx = generate_auth_vector_simulated(uav_supi, long_term_key)
            
            # 🚨 CRITICAL FIX: Store the pending challenge in a separate dictionary 
            # so it is NOT cleared by mine_block()
            self.pending_auth_challenges[uav_supi] = {
                'xres_star': xres_star,
                'ktx_sim': ktx,
                'rand': rand,
                'timestamp': time.time()
            }
            
            # We do NOT mine a block here. We wait for the final AUTH_SUCCESS.

            return {
                'status': 'CHALLENGE_ISSUED',
                'rand': rand,
                'autn': autn,
                'pk_node': 'NodePubKey_Sim' # Public Key shared with UAVs
            }

        elif request_type == 'AUTH_RESPONSE_2':
            # --- AUTH STEP 2: Verify UAV Response (RES*) and establish KTx ---
            res_star_received = request.get('res_star')
            
            # Retrieve the pending challenge from the separate storage
            pending_challenge = self.pending_auth_challenges.get(uav_supi)
            
            if pending_challenge and res_star_received == pending_challenge['xres_star']:
                # Success! Mutual authentication achieved.
                session_key = pending_challenge['ktx_sim']
                
                # Create the SUCCESS transaction and add it to the mining pool
                success_tx = {
                    'tx_id': f'AUTH_SUCCESS_{uav_supi}_{int(time.time())}',
                    'uav_supi': uav_supi,
                    'status': 'AUTHENTICATED',
                    'session_key_sim': session_key, 
                    'auth_rand': pending_challenge['rand']
                }
                self.transaction_pool.append(success_tx)
                
                # Remove the challenge, it's complete
                del self.pending_auth_challenges[uav_supi]
                
                # Immediately mine the AUTH_SUCCESS transaction into the blockchain
                self.mine_block()

                return {'status': 'AUTH_SUCCESS', 'session_key': session_key}
            else:
                return {'status': 'AUTH_FAILURE', 'reason': 'RES* mismatch or no pending challenge'}
                
        elif request_type == 'TELEMETRY_TX':
            # --- POST-AUTH: Handle Telemetry Transaction (TX) ---
            telemetry_data = request.get('data')
            
            # Add the transaction to the pool
            self.transaction_pool.append({
                'tx_id': f'TELEMETRY_{uav_supi}_{int(time.time())}',
                'uav_supi': uav_supi,
                'data': telemetry_data
            })
            
            # Mine a block after a small batch of transactions
            if len(self.transaction_pool) >= 3:
                 self.mine_block()
                 return {'status': 'TX_BLOCK_ACK', 'hash': self.chain[-1]['current_hash'][:10], 'next_hash': self.chain[-1]['current_hash']}
            else:
                 # Send back the current PoH hash seed
                 return {'status': 'TX_RECEIVED', 'hash_seed': self.epoh.latest_hash[:10]}

        return {'status': 'ERROR', 'reason': 'Invalid Request Type'}


    def mine_block(self):
        """Mines a block using the EPOH process and appends it to the chain."""
        if not self.transaction_pool:
            return

        last_hash = self.chain[-1]['current_hash']
        
        # Create the block using the EPOH process
        new_block = self.epoh.create_block(self.transaction_pool, last_hash, len(self.chain))
        
        # Append and save
        self.chain.append(new_block)
        self.save_chain()
        print(f"✅ EPOH Block #{new_block['index']} Mined. TX Count: {len(self.transaction_pool)}. Hash: {new_block['current_hash'][:10]}...")
        
        # Clear the pool only AFTER the block is successfully mined
        self.transaction_pool = []
        

def start_leader_node():
    node = LeaderNode()
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allows quick restart
        s.bind((HOST, PORT))
        s.listen()
        print(f"🚀 EPOH Leader Node ({NODE_ID}) listening on {HOST}:{PORT}")
        
        while True:
            try:
                conn, addr = s.accept()
                with conn:
                    print(f"\nUAV Connected from {addr}")
                    while True:
                        data = conn.recv(4096)
                        if not data:
                            break
                        
                        request = json.loads(data.decode('utf-8'))
                        response = node.handle_uav_request(conn, request)
                        
                        conn.sendall(json.dumps(response).encode('utf-8'))
            
            except Exception as e:
                # Often occurs when the client disconnects gracefully or abruptly
                # print(f"Connection or processing error: {e}") 
                pass

if __name__ == '__main__':
    # Before starting, clear the ledger for a fresh test
    if os.path.exists(LEDGER_FILE):
        os.remove(LEDGER_FILE)
    
    start_leader_node()