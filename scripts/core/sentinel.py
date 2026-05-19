#!/usr/bin/env python3
import subprocess
import os
import time

LOG_FILE = os.path.expanduser("~/.native-agent/pulse.log")
PULSE_SCRIPT = os.path.expanduser("~/.native-agent/scripts/core/pulse.py")

def log(msg):
    print(f"[SENTINEL] {msg}")
    with open(LOG_FILE, "a") as f:
        f.write(f"\n[SENTINEL {time.ctime()}] {msg}\n")

def start_sentinel():
    log("Sentinel Online. Monitoring system journal for critical errors...")
    
    # Watch journalctl for errors (priority err and above) since now
    process = subprocess.Popen(
        ["journalctl", "-p", "err", "-f", "-n", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    buffer = []
    last_trigger = 0
    
    while True:
        line = process.stdout.readline()
        if line:
            buffer.append(line.strip())
            
            # If we get an error and haven't pulsed in the last 2 minutes
            if time.time() - last_trigger > 120:
                # Give it a second to collect related error lines
                time.sleep(1)
                while True:
                    import select
                    r, _, _ = select.select([process.stdout], [], [], 0.1)
                    if r: buffer.append(process.stdout.readline().strip())
                    else: break
                
                error_block = "\n".join(buffer)
                log(f"CRITICAL SYSTEM EVENT DETECTED:\n{error_block}\nTriggering Emergency Reflex Pulse...")
                
                # Write to a temporary file so pulse can read it
                err_path = os.path.expanduser("~/.native-agent/latest_error.txt")
                with open(err_path, "w") as f: f.write(error_block)
                
                # Trigger pulse
                subprocess.Popen(["/home/chrisj/.native-agent/venv/bin/python3", PULSE_SCRIPT, "--emergency"])
                
                buffer = []
                last_trigger = time.time()

if __name__ == "__main__":
    start_sentinel()
