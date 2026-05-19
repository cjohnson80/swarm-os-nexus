#!/usr/bin/env python3
import os
import sys

# DESCRIPTION: A simple file browser skill to help the agent navigate the filesystem.
# USAGE: python3 ~/.native-agent/skills/file_browser.py <directory_path>

def browse(path):
    if not os.path.exists(path):
        print(f"Error: Path {path} does not exist.")
        return
    
    if not os.path.isdir(path):
        print(f"Error: Path {path} is not a directory.")
        return

    print(f"Contents of {path}:")
    try:
        items = os.listdir(path)
        for item in sorted(items):
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                print(f"[DIR]  {item}/")
            else:
                size = os.path.getsize(full_path)
                print(f"[FILE] {item} ({size} bytes)")
    except Exception as e:
        print(f"Error reading directory: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        path = "."
    else:
        path = sys.argv[1]
    browse(path)
