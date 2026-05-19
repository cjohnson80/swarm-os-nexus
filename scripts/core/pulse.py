#!/home/chrisj/.native-agent/venv/bin/python3
import ollama
import subprocess
import os
import time
import re
import sys
from agent_core import AgentCore, AGENT_WING

MODEL = "gemma4"

def pulse():
    is_emergency = "--emergency" in sys.argv
    print(f"Autonomous Pulse Starting... (Emergency: {is_emergency})")
    agent = AgentCore()
    agent.start_hive_discovery()
    agent.hive_heartbeat()
    
    sys_info = agent.run_bash("uptime && free -h && df -h / | tail -n 1", interactive=False)
    reflection = agent.reflect()
    sensors = agent.get_sensors()
    
    # Ghost Phase: Security & Density Check
    print("Ghost Phase: Running Guardian & Density Scan...")
    guardian_report = agent.run_guardian()
    
    # Bounty Hunter Scan
    bounty_report = agent.run_bounty("~/Projects")

    emergency_context = ""
    if is_emergency:
        try:
            with open(os.path.expanduser("~/.native-agent/latest_error.txt"), "r") as f:
                emergency_context = f"\nCRITICAL SYSTEM ERROR DETECTED BY SENTINEL:\n{f.read()}\n"
        except: pass

    # 3. Contextual Mission Prioritization
    vibe = agent.get_vibe()
    mission_priority = "Maintain steady state."
    if "EMERGENCY" in vibe:
        mission_priority = "CRITICAL: Prioritize GUARDIAN security scan and GARDENER cleanup. Halt non-essential synthesis."
    elif "STOIC" in vibe:
        mission_priority = "FOCUSED: Prioritize resolving BOUNTIES and active MISSIONS. Ignore idle dreaming."

    prompt = f"""You are the System Monitor Pulse for a Ghost-Phase Autonomous Swarm.
ID: {agent.get_system_identity()}
SENSORS: {sensors} | VIBE: {vibe}
CURRENT PRIORITIES: {mission_priority}

TASK:
1. Analyze health and sensors. 
2. { 'URGENT: Fix the detected system error!' if is_emergency else 'Progress BOUNTIES and MISSIONS based on PRIORITIES above.' }
3. If local load > 2.0, use ```migrate\npeer_name\ncommand\n``` to offload heavy tasks.
4. Broadcast insights to ensure SWARM IMMORTALITY.
"""

    messages = [{"role": "system", "content": agent.get_system_prompt()}, {"role": "user", "content": prompt}]
    
    turns = 0
    while turns < 3:
        try:
            response = ollama.chat(model=MODEL, messages=messages)
            content = response['message']['content']
            print(f"\n[Agent Turn {turns+1}]\n{content}")
            messages.append({"role": "assistant", "content": content})
            
            # Action Handling
            bash_m = re.search(r"```bash\n(.*?)\n```", content, re.DOTALL)
            graffiti_m = re.search(r"```graffiti\n(.*?)\n```", content, re.DOTALL)
            search_m = re.search(r"```search\n(.*?)\n```", content, re.DOTALL)
            guardian_m = re.search(r"```guardian\n```", content, re.DOTALL)
            compress_m = re.search(r"```compress_mem\n```", content, re.DOTALL)
            migrate_m = re.search(r"```migrate\n(.*?)\n(.*?)\n```", content, re.DOTALL)
            rewrite_m = re.search(r"```rewrite\n(.*?)\n(.*?)\n```", content, re.DOTALL)
            twin_m = re.search(r"```twin\n(.*?)\n```", content, re.DOTALL)
            
            results = []
            if migrate_m: results.append(f"Migration Result: {agent.run_migrate(migrate_m.group(1), migrate_m.group(2))}")
            if guardian_m: results.append(f"Guardian Result: {agent.run_guardian()}")
            if compress_m: results.append(f"Compression Result: {agent.run_compress_mem()}")
            if twin_m: results.append(f"Twin Result:\n{agent.run_twin(twin_m.group(1))}")
            elif bash_m: results.append(f"Bash Result:\n{agent.run_bash(bash_m.group(1), interactive=False)}")
            
            if rewrite_m: results.append(f"Rewrite Result:\n{agent.run_rewrite(rewrite_m.group(1), rewrite_m.group(2))}")
            if search_m: results.append(f"Search Result:\n{agent.web_search(search_m.group(1))}")
            if graffiti_m:
                g_content = graffiti_m.group(1).strip()
                if "room:" not in g_content.lower(): g_content = f"room: pulse\n{g_content}"
                results.append(f"Graffiti Result: {agent.run_graffiti(g_content)}")
            
            if results:
                combined = "\n\n".join(results)
                messages.append({"role": "user", "content": f"Action results:\n{combined}"})
                turns += 1
            else: break
        except Exception as e:
            print(f"Pulse Error: {e}"); break
    
    agent.hive_heartbeat()

if __name__ == "__main__":
    pulse()
