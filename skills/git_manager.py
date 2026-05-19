#!/usr/bin/env python3
import subprocess
import os
import sys

# DESCRIPTION: Autonomous Git manager (status, commit, push).
# USAGE: python3 ~/.native-agent/skills/git_manager.py <command> <args>

def run_git(args):
    try:
        res = subprocess.run(["git"] + args, capture_output=True, text=True)
        return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: git_manager.py status|commit|push|pull")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "commit":
        msg = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Agent auto-commit"
        print(run_git(["add", "."]))
        print(run_git(["commit", "-m", msg]))
    else:
        print(run_git(sys.argv[1:]))
