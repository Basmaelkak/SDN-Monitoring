# File: attack.py
# A simple script to generate control plane activity.

import socket
import time
import random

# --- Attack Configuration ---
TARGET_IP = "10.0.0.2"
NUMBER_OF_PORTS_TO_ATTACK = 200
DELAY_BETWEEN_PACKETS = 0.1
# -----------------------------

print(f"--- Starting simulation attack on {TARGET_IP} ---")
print(f"Attempting to connect to {NUMBER_OF_PORTS_TO_ATTACK} different ports...")
print(f"Attack will last approximately {NUMBER_OF_PORTS_TO_ATTACK * DELAY_BETWEEN_PACKETS:.1f} seconds.")

for port in range(1, NUMBER_OF_PORTS_TO_ATTACK + 1):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        s.connect_ex((TARGET_IP, port))
        s.close()
        
        # Print a dot to show progress (optional)
        print(".", end='', flush=True)

    except (socket.error, ConnectionRefusedError):
        # Errors are expected, just ignore them.
        pass
    
    time.sleep(DELAY_BETWEEN_PACKETS)

print("\n--- Attack finished. ---")