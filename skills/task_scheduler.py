#!/usr/bin/env python3
import subprocess
import os
import sys

# DESCRIPTION: Schedules future tasks using 'at'.
# USAGE: python3 ~/.native-agent/skills/task_scheduler.py <time_string> <command>
# EXAMPLE: task_scheduler.py "now + 2 hours" "notify-send 'Hello'"

def schedule(time_str, command):
    try:
        # Check if 'at' is installed
        subprocess.run(["at", "-V"], capture_output=True, check=True)
        
        process = subprocess.Popen(["at", time_str], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(input=command)
        
        if process.returncode == 0:
            print(f"Task scheduled for {time_str}: {command}")
            print(stderr)
        else:
            print(f"Error scheduling task: {stderr}")
    except FileNotFoundError:
        print("Error: 'at' command not found. Please install it (e.g., sudo apt install at).")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: task_scheduler.py '<time>' '<command>'")
        sys.exit(1)
    schedule(sys.argv[1], sys.argv[2])
