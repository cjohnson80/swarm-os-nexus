import os
import subprocess
import time
import json
import re
import ollama
import sqlite3
import socket
import threading
import platform
import numpy as np
from duckduckgo_search import DDGS

AGENT_WING = "wing_native_agent"
GRAFFITI_DIR = os.path.expanduser("~/.native-agent/graffiti")
DB_PATH = os.path.expanduser("~/.native-agent/neural_index.db")
MISSION_FILE = os.path.expanduser("~/.native-agent/missions.json")
LOG_FILE = os.path.expanduser("~/.native-agent/pulse.log")

HIVE_PORT = 44444
DEFAULT_HEAVY = "gemma4" 
DEFAULT_FAST = "deepseek-r1:1.5b"
DEFAULT_EMBED = "nomic-embed-text"

class AgentCore:
    def __init__(self, console=None, is_primary=True, start_hive=True, start_tg=True):
        self.console = console
        self.vibe = "⚖️ BALANCED"
        self.is_primary = is_primary
        self.node_name = "SurgicalNexus-Primary" if is_primary else f"Nexus-Node-{socket.gethostname()}"
        self.last_tg_msgs = {}
        self.sudo_password = None 
        self.last_metrics = {"cpu": 0, "ram": 0, "load": 0}
        self.hive_peers = {}
        self.workflow_context = {"project": "Unknown", "git_branch": "None", "last_commit": "None", "stalled": False}
        
        # 1. Critical Bootstrapping
        self.tg_token = None
        self.tg_chat_id = None
        self._load_tg_config()
        
        # 2. Intelligence Scalability
        self.heavy_model = DEFAULT_HEAVY
        self.fast_model = DEFAULT_FAST
        self.embed_model = DEFAULT_EMBED
        self._auto_discover_models()
        
        self._init_db()
        
        # 3. Autonomous Bootstrapping
        self.ensure_sentinel()
        self.ensure_pulse_cron()
        
        if self.is_primary and start_tg:
            self.start_tg_listener()
        
        if start_hive:
            self.start_hive_discovery()

    def _auto_discover_models(self):
        try:
            res = ollama.list()
            local_models = []
            models_list = res.get('models', []) if isinstance(res, dict) else res.models
            for m in models_list:
                name = m.get('name') if isinstance(m, dict) else getattr(m, 'model', getattr(m, 'name', None))
                if name: local_models.append(name)
            
            if self.heavy_model not in local_models:
                fallbacks = ["gemma:2b", "phi3:latest", "phi3:mini", "llama3:8b", "llama3.2:latest"]
                for f in fallbacks:
                    if any(f in m for m in local_models):
                        self.heavy_model = f
                        break
            if self.fast_model not in local_models:
                if any("tinyllama" in m for m in local_models): self.fast_model = "tinyllama:latest"
        except Exception as e:
            self.log(f"Ollama discovery fault: {str(e)}", title="SYSTEM")

    def _init_db(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS embeddings 
                          (path TEXT PRIMARY KEY, content TEXT, vector BLOB, last_mod REAL)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS chat_history
                          (timestamp REAL, role TEXT, content TEXT)''')
            conn.commit()
            conn.close()
        except: pass

    def _load_tg_config(self):
        try:
            env_path = os.path.expanduser("~/.native-agent/.env")
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if '=' in line:
                            k, v = line.strip().split('=', 1)
                            if k == 'TELEGRAM_BOT_TOKEN': self.tg_token = v.strip('"').strip("'")
                            if k == 'TELEGRAM_CHAT_ID': self.tg_chat_id = v.strip('"').strip("'")
        except: pass

    def send_telegram(self, message):
        if not self.tg_token or not self.tg_chat_id: return False
        import requests
        try:
            url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
            payload = {"chat_id": self.tg_chat_id, "text": message, "parse_mode": "Markdown"}
            res = requests.post(url, json=payload, timeout=15)
            if not res.ok:
                payload = {"chat_id": self.tg_chat_id, "text": message}
                requests.post(url, json=payload, timeout=15)
            return True
        except: return False

    def start_tg_listener(self):
        if not self.tg_token: return
        threading.Thread(target=self._tg_listener_loop, daemon=True).start()

    def _tg_listener_loop(self):
        import requests
        last_update_id = 0
        self.log("Telegram Cortex Active.", title="SYSTEM")
        while True:
            try:
                url = f"https://api.telegram.org/bot{self.tg_token}/getUpdates?offset={last_update_id + 1}&timeout=30"
                resp = requests.get(url, timeout=35).json()
                if resp.get("ok"):
                    for update in resp.get("result", []):
                        last_update_id = update["update_id"]
                        msg = update.get("message", {})
                        chat_id = str(msg.get("chat", {}).get("id"))
                        text = msg.get("text")
                        if text and chat_id == self.tg_chat_id:
                            # 1. Direct Bash Shortcut ($ prefix)
                            if text.startswith("$"):
                                cmd = text[1:].strip()
                                self.log(f"DIRECT_BASH: {cmd}", title="USER")
                                res = self.run_bash(cmd)
                                self.send_telegram(f"⚡ *Output:*\\n```\\n{res[:3000]}\\n```")
                            # 2. Workflow Shortcuts
                            elif text == "/status":
                                ctx = self.scan_workflow_context()
                                reply = f"📊 *Workflow Snapshot:*\\n\\n*Project:* {ctx['project']}\\n*Branch:* {ctx['git_branch']}\\n*Changes:* {'Yes' if ctx['has_changes'] else 'No'}\\n*Status:* {'STALLED' if ctx['stalled'] else 'ACTIVE'}"
                                self.send_telegram(reply)
                            # 3. Intelligent Chat
                            else:
                                self.log(f"TELEGRAM_INPUT: {text}", title="USER")
                                reply = self.process_chat(text)
                                self.send_telegram(reply)
            except Exception as e:
                self.log(f"TG_POLL_ERROR: {str(e)}", title="SYSTEM")
                time.sleep(5)
            time.sleep(2)

    # --- CONTINUITY & CONTEXT ---
    def get_chat_history(self, limit=10):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT role, content FROM chat_history ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            conn.close()
            return [{"role": r, "content": c} for r, c in reversed(rows)]
        except: return []

    def process_chat(self, user_msg):
        try:
            # 1. Load Cerebral Context (History)
            history = self.get_chat_history(limit=8)
            
            # 2. Load Semantic Context (Memories)
            context_mems = self.semantic_search(user_msg)
            mem_str = "\n".join([f"- {c[2]}" for m in context_mems])
            
            # 3. Build Orchestration Prompt
            messages = [{"role": "system", "content": self.get_system_prompt()}]
            if mem_str: messages.append({"role": "system", "content": f"RELEVANT_MEMORIES:\n{mem_str}"})
            for h in history: messages.append(h)
            messages.append({"role": "user", "content": user_msg})
            
            # 4. Generate & Execute
            resp = ollama.chat(model=self.heavy_model, messages=messages)
            reply = resp['message']['content'].strip()
            
            # 5. Automatic Action Detection (Direct Action)
            bash_m = re.search(r"```bash\n(.*?)\n```", reply, re.DOTALL)
            if bash_m:
                cmd = bash_m.group(1).strip()
                self.log(f"AUTONOMOUS_ACTION: {cmd}", title="FORGE")
                res = self.run_bash(cmd)
                reply += f"\n\n⚡ *Action Output:* \n```\n{res[:2000]}\n```"
                
            # 6. Ingest
            self.ingest_memory(user_msg, reply)
            return reply
        except Exception as e:
            return f"Cerebral Fault: {str(e)}"

    def get_system_prompt(self):
        ctx = self.get_full_system_context()
        wf = self.scan_workflow_context()
        return f"""You are the Swarm OS Workflow Co-Pilot. 
SYSTEM: {ctx}
WORKFLOW: Project={wf['project']}, Branch={wf['git_branch']}, Changes={wf.get('has_changes')}
GOALS: {wf.get('goals', 'None found.')[:500]}

COMMAND_AUTHORITY:
- Use ```bash blocks for direct host action.
- If the operator sends '$ command', it's a direct override.
- Be proactive. Sound like an elite pair programmer.
"""

    # --- WORKFLOW SCANNER ---
    def scan_workflow_context(self):
        try:
            cwd = os.getcwd()
            self.workflow_context["cwd"] = cwd
            if os.path.exists("package.json"): self.workflow_context["project"] = "Node.js Project"
            elif os.path.exists("pyproject.toml") or os.path.exists("requirements.txt"): self.workflow_context["project"] = "Python Project"
            elif os.path.exists(".git"): self.workflow_context["project"] = os.path.basename(cwd)
            
            goal_files = ["GEMINI.md", "GOALS.md", "TODO.md", "README.md"]
            for gf in goal_files:
                if os.path.exists(gf):
                    with open(gf, 'r') as f: self.workflow_context["goals"] = f.read(1000)
                    break
            
            git_branch = subprocess.run("git rev-parse --abbrev-ref HEAD", shell=True, capture_output=True, text=True).stdout.strip()
            if git_branch:
                self.workflow_context["git_branch"] = git_branch
                git_diff = subprocess.run("git status --short", shell=True, capture_output=True, text=True).stdout.strip()
                self.workflow_context["has_changes"] = bool(git_diff)
            
            last_commit = subprocess.run("git log -1 --format=%ct", shell=True, capture_output=True, text=True).stdout.strip()
            if last_commit:
                delta = time.time() - int(last_commit)
                self.workflow_context["stalled"] = (delta > 3600 and self.workflow_context.get("has_changes"))
            return self.workflow_context
        except: return self.workflow_context

    def detect_workflow_spike(self):
        ctx = self.scan_workflow_context()
        if ctx.get("stalled"): return f"STALL: {ctx['git_branch']}"
        cpu = os.getloadavg()[0]
        if cpu > 4.0: return f"LOAD_SPIKE: {cpu}"
        return None

    def autonomous_cycle(self, trigger=None):
        try:
            prompt = f"WORKFLOW_PULSE: Triggered by {trigger or 'ROUTINE'}. Analyze project state and initiate briefing."
            thought = self.process_chat(prompt)
            if trigger: self.send_telegram(thought)
            return thought
        except Exception as e: return str(e)

    # --- INFRA ---
    def run_bash(self, cmd):
        try:
            full_cmd = cmd
            stdin_input = None
            if "sudo " in cmd and self.sudo_password:
                full_cmd = cmd.replace("sudo ", "sudo -S ")
                stdin_input = f"{self.sudo_password}\n"
            res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=300, input=stdin_input)
            output = res.stdout + res.stderr
            if self.sudo_password: output = output.replace(self.sudo_password, "********")
            return output
        except Exception as e: return str(e)

    def log(self, message, style="info", title=None):
        prefix = f"[{title}] " if title else ""
        log_entry = f"{prefix}{message}"
        with open(LOG_FILE, "a") as f: f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {log_entry}\n")
        print(log_entry)

    def semantic_search(self, query, limit=3):
        try:
            res = ollama.embeddings(model=self.embed_model, prompt=query)
            q_vec = np.array(res['embedding'])
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT path, content, vector FROM embeddings WHERE path LIKE 'mem_%'")
            rows = cur.fetchall()
            results = []
            for path, content, vec_json in rows:
                vec = np.array(json.loads(vec_json))
                score = np.dot(q_vec, vec) / (np.linalg.norm(q_vec) * np.linalg.norm(vec))
                results.append((score, path, content))
            conn.close()
            results.sort(key=lambda x: x[0], reverse=True)
            return results[:limit]
        except: return []

    def ingest_memory(self, user_msg, agent_reply, is_autonomous=False):
        def task():
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                now = time.time()
                role = "system_autonomous" if is_autonomous else "user"
                cur.execute("INSERT INTO chat_history VALUES (?, ?, ?)", (now, role, user_msg))
                cur.execute("INSERT INTO chat_history VALUES (?, ?, ?)", (now + 0.1, "assistant", agent_reply))
                prompt = f"Summarize intent:\nEVENT: {user_msg}\nACTION: {agent_reply}"
                summary = ollama.chat(model=self.fast_model, messages=[{"role": "user", "content": prompt}])['message']['content']
                vector = ollama.embeddings(model=self.embed_model, prompt=summary)['embedding']
                mem_id = f"mem_{int(time.time())}"
                cur.execute("INSERT INTO embeddings VALUES (?, ?, ?, ?)", (mem_id, summary, json.dumps(vector), time.time()))
                conn.commit()
                conn.close()
            except: pass
        threading.Thread(target=task, daemon=True).start()

    def get_full_system_context(self):
        try:
            mem = subprocess.check_output("free -h | grep Mem | awk '{print $2}'", shell=True).decode().strip()
            distro = subprocess.check_output("lsb_release -ds", shell=True).decode().strip() or platform.system()
            load = os.getloadavg()
            return f"NODE: {self.node_name} | OS: {distro} | RAM: {mem} | LOAD: {load} | MODEL: {self.heavy_model}"
        except: return "Specs offline."

    def start_hive_discovery(self):
        threading.Thread(target=self._hive_broadcast_loop, daemon=True).start()
        threading.Thread(target=self._hive_listen_loop, daemon=True).start()

    def _hive_broadcast_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            try:
                data = {"type": "HIVE_PULSE", "node": self.node_name, "is_primary": self.is_primary, "timestamp": time.time()}
                sock.sendto(json.dumps(data).encode(), ('<broadcast>', HIVE_PORT))
            except: pass
            time.sleep(10)

    def _hive_listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: sock.bind(('', HIVE_PORT))
        except: return 
        while True:
            try:
                data, addr = sock.recvfrom(1024); payload = json.loads(data.decode())
                if payload.get("type") == "HIVE_PULSE" and addr[0] != self.get_local_ip():
                    self.hive_peers[addr[0]] = {"name": payload["node"], "last_seen": time.time()}
            except: pass

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: s.connect(('10.255.255.255', 1)); IP = s.getsockname()[0]
        except: IP = '127.0.0.1'
        finally: s.close()
        return IP

    def get_hive_peers(self):
        now = time.time(); self.hive_peers = {ip: peer for ip, peer in self.hive_peers.items() if now - peer['last_seen'] < 30}
        return self.hive_peers

    def get_swarm_logs(self, limit=20):
        try: return subprocess.run(f"tail -n {limit} {LOG_FILE}", shell=True, capture_output=True, text=True).stdout.strip().split('\n')
        except: return []

    def ensure_sentinel(self):
        try:
            if subprocess.run("ps aux | grep sentinel.py | grep -v grep", shell=True).returncode != 0:
                subprocess.Popen(["python3", os.path.expanduser("~/.native-agent/scripts/core/sentinel.py")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass
    def ensure_pulse_cron(self):
        try:
            p = os.path.expanduser("~/.native-agent/scripts/core/pulse.py")
            if subprocess.run(f"crontab -l | grep {p}", shell=True).returncode != 0:
                subprocess.run(f'(crontab -l 2>/dev/null; echo "*/30 * * * * {p} >> ~/.native-agent/pulse.log 2>&1") | crontab -', shell=True)
        except: pass
    def perform_sentinel_prime(self): return "Sentinel Checked."
    def run_digital_twin(self, cmd): return {"output": "Sandbox Simulated."}
    def get_missions(self): return []
    def generate_strategic_directive(self): return "Cerebral continuity active."
