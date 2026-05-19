#!/usr/bin/env python3
import subprocess
import os
import sys

# DESCRIPTION: Captures error tracebacks and environment info for iterative debugging.
# USAGE: python3 ~/.native-agent/skills/code_debugger.py <script_to_run>

def debug_run(script_path):
    print(f"--- Debug Run: {script_path} ---")
    if not os.path.exists(script_path):
        print("Error: File not found.")
        return

    ext = os.path.splitext(script_path)[1]
    cmd = []
    if ext == ".py": cmd = ["python3", script_path]
    elif ext == ".sh": cmd = ["bash", script_path]
    else: cmd = [script_path]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            print("SUCCESS: Script ran without errors.")
            print(f"Output:\n{res.stdout}")
        else:
            print(f"FAILURE (Exit Code {res.returncode})")
            print(f"--- STDOUT ---\n{res.stdout}")
            print(f"--- STDERR (TRACEBACK) ---\n{res.stderr}")
    except subprocess.TimeoutExpired:
        print("FAILURE: Script timed out after 30 seconds.")
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: code_debugger.py <path_to_script>")
        sys.exit(1)
    debug_run(sys.argv[1])
