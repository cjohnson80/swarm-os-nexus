import os
import subprocess
import time
import threading

# v29.1 Stress Test Simulation
# Purpose: Flood the Swarm Fabric within the Digital Twin Shadow-Root

ROOT = os.path.expanduser("~/.native-agent")

def simulate_fs_load():
    print("[SIM] Triggering recursive file creation...")
    for i in range(50):
        with open(f"stress_file_{i}.tmp", 'w') as f:
            f.write("STRESS_TEST_DATA_" * 100)
    print("[SIM] FS Load Complete.")

def simulate_blackboard_flood():
    print("[SIM] Flooding Blackboard registry...")
    for i in range(20):
        # Emulating the memory.js call
        subprocess.run(f"node {ROOT}/scripts/memory.js set 'STRESS_KEY_{i}' 'BURST_DATA_{i}'", shell=True)
    print("[SIM] Blackboard Flood Complete.")

if __name__ == "__main__":
    print("--- STARTING TWIN STRESS TEST v29.1 ---")
    start = time.time()
    
    t1 = threading.Thread(target=simulate_fs_load)
    t2 = threading.Thread(target=simulate_blackboard_flood)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    print(f"--- STRESS TEST COMPLETE in {time.time() - start:.2f}s ---")
