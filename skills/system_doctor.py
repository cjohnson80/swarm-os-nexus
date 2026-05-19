#!/usr/bin/env python3
import subprocess
import os
import sys

# DESCRIPTION: Diagnostic tool for deep system health checks (failed services, heavy load, thermal).
# USAGE: python3 ~/.native-agent/skills/system_doctor.py

def check_failed_services():
    print("--- [ Failed Systemd Services ] ---")
    res = subprocess.run("systemctl --failed --no-legend", shell=True, capture_output=True, text=True)
    print(res.stdout if res.stdout.strip() else "All services running fine.")

def check_heavy_processes():
    print("\n--- [ Top 5 Memory/CPU Consumers ] ---")
    res = subprocess.run("ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%mem | head -n 6", shell=True, capture_output=True, text=True)
    print(res.stdout)

def check_system_errors():
    print("\n--- [ Recent Kernel Errors (dmesg) ] ---")
    res = subprocess.run("dmesg | tail -n 20 | grep -i 'error\\|fail\\|warn'", shell=True, capture_output=True, text=True)
    print(res.stdout if res.stdout.strip() else "No recent kernel errors detected.")

def check_disk_health():
    print("\n--- [ Disk Pressure ] ---")
    res = subprocess.run("df -h /", shell=True, capture_output=True, text=True)
    print(res.stdout)

if __name__ == "__main__":
    check_failed_services()
    check_heavy_processes()
    check_system_errors()
    check_disk_health()
