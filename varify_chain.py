import json
import hashlib
import sys
import os

def hash_block(block):
    """Calculates the SHA-256 hash of a block by ensuring deterministic JSON output."""
    # Temporarily remove the 'current_hash' field before hashing, if it exists
    temp_block = block.copy()
    if 'current_hash' in temp_block:
        del temp_block['current_hash'] 
        
    # JSON dump must be sorted for the hash to be consistent (deterministic)
    block_string = json.dumps(temp_block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()

def is_valid_chain():
    """
    Verifies the entire EPOH ledger by checking cryptographic links and chronology.
    """
    print(f"\n--- Verifying EPOH Ledger: {os.path.abspath('epoh_ledger.json')} ---")
    
    try:
        with open('epoh_ledger.json', 'r') as f:
            chain = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return False, "Ledger file missing or corrupted (JSON Syntax Error)."

    if not chain:
        return False, "Chain is empty."
    
    # 1. Check Genesis Block (Index 0)
    if chain[0]['previous_hash'] != '0':
        return False, "Genesis Block (Index 0) has an invalid previous_hash."
    
    # 2. Iterate through the rest of the chain (starting from Index 1)
    for i in range(1, len(chain)):
        current_block = chain[i]
        previous_block = chain[i-1]
        
        # --- A. Integrity Check (The Core Proof of Immutability) ---
        # Recalculate the hash of the PREVIOUS block as stored in the ledger
        recalculated_hash = hash_block(previous_block)
        
        # Compare the recalculated hash to the CURRENT block's 'previous_hash' field
        if current_block['previous_hash'] != recalculated_hash:
             print(f"FAILED AT BLOCK #{i}: Corrupted Linkage Detected.")
             print(f"  Expected Hash of #{i-1}: {current_block['previous_hash']}")
             print(f"  Actual Recalculated Hash: {recalculated_hash}")
             return False, f"Integrity Failure: Block #{i} links to tampered block #{i-1}."

        # --- B. Chronology Check (The PoH Aspect) ---
        # Ensure the timestamp is strictly increasing (proving sequential history)
        if current_block['timestamp'] <= previous_block['timestamp']:
             return False, f"PoH Chronology Failure: Block #{i} timestamp is not strictly greater than block #{i-1}."
    
    return True, "Chain is fully valid."

# --- Execution ---
if __name__ == '__main__':
    is_valid, reason = is_valid_chain()

    if not is_valid:
        print(f"\n🚨🚨🚨 CHAIN VERIFICATION FAILED! TAMPERING OR CORRUPTION DETECTED. 🚨🚨🚨")
        print(f"REASON: {reason}")
    else:
        print("\n✅ EPOH LEDGER IS VALID. INTEGRITY AND CHRONOLOGY CONFIRMED.")