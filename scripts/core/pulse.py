#!/home/chrisj/.native-agent/venv/bin/python3
import subprocess
import os
import time
import re
import sys

# Ensure we can find AgentCore
sys.path.append(os.path.join(os.path.dirname(__file__)))
from agent_core import AgentCore

def pulse():
    is_emergency = "--emergency" in sys.argv
    print(f"Workflow Pulse Starting... (Emergency: {is_emergency})")
    
    # Initialize agent: start_hive=False to avoid port conflicts with the running portal
    agent = AgentCore(is_primary=True, start_hive=False)
    
    # 1. Workflow Heuristics (Proactive Intelligence)
    workflow_trigger = agent.detect_workflow_spike()
    if workflow_trigger or is_emergency:
        print(f"Workflow Spike Detected: {workflow_trigger}")
        # This will autonomously initiate a Telegram conversation
        agent.autonomous_cycle(trigger=workflow_trigger)
    else:
        print("System and Workflow stable. No intervention required.")
    
    # 2. System Sentinel
    agent.perform_sentinel_prime()
    
    print("Pulse Complete.")

if __name__ == "__main__":
    pulse()
