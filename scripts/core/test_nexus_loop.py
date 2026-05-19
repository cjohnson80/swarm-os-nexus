import ollama
import re
import sys
import os

# Ensure we can import agent_core
sys.path.append(os.path.expanduser("~/.native-agent/scripts/core"))
from agent_core import AgentCore

def test_optimization_loop():
    agent = AgentCore()
    
    print("--- STEP 1: NEURAL ANALYSIS ---")
    prompt = "Analyze the current system state and suggest ONE specific optimization. Provide the bash command to rehearse this optimization in the Digital Twin."
    messages = [
        {"role": "system", "content": agent.get_system_prompt()},
        {"role": "user", "content": prompt}
    ]
    
    try:
        resp = ollama.chat(model="gemma4", messages=messages)
        reply = resp['message']['content']
        print(reply)
        
        bash_m = re.search(r"```bash\n(.*?)\n```", reply, re.DOTALL)
        if bash_m:
            cmd = bash_m.group(1).strip()
            print(f"\n--- STEP 2: HARDENED REHEARSAL (BWRAP) ---")
            print(f"Executing in Sandbox: {cmd}")
            res = agent.run_digital_twin(cmd)
            print("\n--- SANDBOX OUTPUT ---")
            print(res['output'])
        else:
            print("\n[!] No bash command found in reasoning.")
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    test_optimization_loop()
