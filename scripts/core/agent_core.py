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
HEAVY_MODEL = "gemma4" 
FAST_MODEL = "deepseek-r1:1.5b"
EMBED_MODEL = "nomic-embed-text"

class AgentCore:
    def __init__(self, console=None, is_primary=True):
        self.console = console
        self.vibe = "⚖️ BALANCED"
        self.is_primary = is_primary
        self.node_name = "SurgicalNexus-Primary" if is_primary else f"Nexus-Node-{socket.gethostname()}"
        self.last_tg_msgs = {}
        self.sudo_password = None 
        self.last_metrics = {"cpu": 0, "ram": 0, "load": 0}
        self.hive_peers = {} # {ip: {name: str, last_seen: float, metrics: dict}}
        
        self._load_tg_config()
        self._init_db()
        
        # Autonomous Bootstrapping
        self.ensure_sentinel()
        self.ensure_pulse_cron()
        if self.is_primary:
            self.start_tg_listener()
        
        # Hive Activation
        self.start_hive_discovery()

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

    def set_sudo(self, password):
        self.sudo_password = password
        return True

    def _load_tg_config(self):
        self.tg_token = None
        self.tg_chat_id = None
        try:
            env_path = os.path.expanduser("~/.native-agent/.env")
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if '=' in line:
                            k, v = line.strip().split('=', 1)
                            if k == 'TELEGRAM_BOT_TOKEN': self.tg_token = v.strip('"')
                            if k == 'TELEGRAM_CHAT_ID': self.tg_chat_id = v.strip('"')
        except: pass

    def send_telegram(self, message):
        if not self.tg_token or not self.tg_chat_id: return False
        now = time.time()
        if message in self.last_tg_msgs and (now - self.last_tg_msgs[message] < 300):
            return False
        import requests
        try:
            url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
            payload = {"chat_id": self.tg_chat_id, "text": message, "parse_mode": "Markdown"}
            requests.post(url, json=payload, timeout=10)
            self.last_tg_msgs[message] = now
            return True
        except: return False

    def start_tg_listener(self):
        if not self.tg_token: return
        threading.Thread(target=self._tg_listener_loop, daemon=True).start()

    def _tg_listener_loop(self):
        import requests
        last_update_id = 0
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
                            common_cmds = ['ls', 'uptime', 'whoami', 'df', 'free', 'ps', 'top', 'pkill']
                            is_bash = text.startswith('/') or text.split()[0] in common_cmds
                            if is_bash:
                                cmd = text[1:] if text.startswith('/') else text
                                res = self.run_bash(cmd)
                                self.send_telegram(f"⚡ *BASH OUTPUT:*\\n```\\n{res[:3000]}\\n```")
                            else:
                                reply = self.process_chat(text)
                                self.send_telegram(reply)
            except: time.sleep(5)
            time.sleep(2)

    # --- HIVE LOGIC ---
    def start_hive_discovery(self):
        """Broadcasts presence and listens for peers."""
        threading.Thread(target=self._hive_broadcast_loop, daemon=True).start()
        threading.Thread(target=self._hive_listen_loop, daemon=True).start()

    def _hive_broadcast_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            try:
                metrics = {
                    "cpu": os.getloadavg()[0],
                    "ram": float(subprocess.check_output("free | grep Mem | awk '{print $3/$2 * 100.0}'", shell=True).decode().strip())
                }
                data = {
                    "type": "HIVE_PULSE",
                    "node": self.node_name,
                    "is_primary": self.is_primary,
                    "metrics": metrics,
                    "timestamp": time.time()
                }
                sock.sendto(json.dumps(data).encode(), ('<broadcast>', HIVE_PORT))
            except: pass
            time.sleep(10)

    def _hive_listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', HIVE_PORT))
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                payload = json.loads(data.decode())
                if payload.get("type") == "HIVE_PULSE" and addr[0] != self.get_local_ip():
                    if addr[0] not in self.hive_peers:
                        self.log(f"NEW HIVE NODE DETECTED: {payload['node']} @ {addr[0]}", title="HIVE")
                    self.hive_peers[addr[0]] = {
                        "name": payload["node"],
                        "is_primary": payload["is_primary"],
                        "metrics": payload["metrics"],
                        "last_seen": time.time()
                    }
                    if payload["is_primary"] and not self.is_primary:
                        self.log(f"HIVE_CONTROLLER DETECTED: {payload['node']} @ {addr[0]}", title="HIVE")
            except: pass

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except: IP = '127.0.0.1'
        finally: s.close()
        return IP

    def get_hive_peers(self):
        now = time.time()
        # Cleanup stale peers (>30s)
        self.hive_peers = {ip: peer for ip, peer in self.hive_peers.items() if now - peer['last_seen'] < 30}
        return self.hive_peers

    # --- CORE LOGIC ---
    def semantic_search(self, query, limit=3):
        try:
            res = ollama.embeddings(model=EMBED_MODEL, prompt=query)
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
                prompt = f"Summarize intent/nuance for long-term memory:\nEVENT: {user_msg}\nACTION: {agent_reply}"
                summary = ollama.chat(model=FAST_MODEL, messages=[{"role": "user", "content": prompt}])['message']['content']
                vector = ollama.embeddings(model=EMBED_MODEL, prompt=summary)['embedding']
                mem_id = f"mem_{int(time.time())}"
                cur.execute("INSERT INTO embeddings VALUES (?, ?, ?, ?)", 
                            (mem_id, summary, json.dumps(vector), time.time()))
                conn.commit()
                conn.close()
                self.log(f"Memory Reflected: {mem_id}", title="NEURAL_INGEST")
            except: pass
        threading.Thread(target=task, daemon=True).start()

    def get_chat_history(self, limit=20):
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
            context_mems = self.semantic_search(user_msg)
            context_str = "\n".join([f"- {c[2]}" for c in context_mems])
            prompt = self.get_system_prompt()
            messages = [
                {"role": "system", "content": prompt},
                {"role": "system", "content": f"RELEVANT_MEMORIES:\n{context_str}" if context_str else "No relevant memories found."},
                {"role": "user", "content": user_msg}
            ]
            resp = ollama.chat(model=HEAVY_MODEL, messages=messages)
            reply = resp['message']['content'].strip()
            bash_m = re.search(r"```bash\n(.*?)\n```", reply, re.DOTALL)
            if bash_m:
                cmd = bash_m.group(1).strip()
                res = self.run_bash(cmd)
                reply += f"\n\n⚡ *Execution Output:* \n```\n{res[:2000]}\n```"
            self.ingest_memory(user_msg, reply)
            return reply
        except: return "My reasoning core is momentarily offline."

    def detect_neural_spike(self):
        try:
            cpu = os.getloadavg()[0]
            ram = float(subprocess.check_output("free | grep Mem | awk '{print $3/$2 * 100.0}'", shell=True).decode().strip())
            if ram > 85: return f"HIGH_MEMORY_PRESSURE: {ram:.1f}%"
            if cpu > 3.0: return f"HIGH_CPU_LOAD: {cpu:.2f}"
            if abs(ram - self.last_metrics["ram"]) > 10:
                self.last_metrics["ram"] = ram
                return f"MEMORY_SHIFT_DETECTED: {ram:.1f}%"
            logs = self.get_swarm_logs(limit=5)
            for log in logs:
                if "ERROR" in log or "CRITICAL" in log or "FAILED" in log:
                    return f"CRITICAL_LOG_EVENT: {log[:50]}"
            self.last_metrics["ram"] = ram
            return None
        except: return None

    def autonomous_cycle(self, trigger=None):
        try:
            ctx = self.get_full_system_context()
            prompt = f"EVENT_DRIVEN_REFLECTION:\nTRIGGER: {trigger or 'PERIODIC_PULSE'}\nSYSTEM_STATE: {ctx}\nDetermine if intervention is needed. Concise."
            resp = ollama.chat(model=FAST_MODEL, messages=[{"role": "system", "content": self.get_system_prompt()}, {"role": "user", "content": prompt}])
            thought = resp['message']['content'].strip()
            self.log(f"HEURISTIC_PULSE [{trigger or 'PULSE'}]: {thought[:200]}...", title="NEURAL_PULSE")
            self.ingest_memory(f"TRIGGER: {trigger}", thought, is_autonomous=True)
            return thought
        except Exception as e: return f"Consciousness Glitch: {str(e)}"

    def get_full_system_context(self):
        try:
            mem = subprocess.check_output("free -h | grep Mem | awk '{print $2}'", shell=True).decode().strip()
            distro = subprocess.check_output("lsb_release -ds", shell=True).decode().strip() or platform.system()
            load = os.getloadavg()
            return f"NODE: {self.node_name} | ROLE: {'PRIMARY' if self.is_primary else 'NODE'} | OS: {distro} | RAM: {mem} | LOAD: {load}"
        except: return "Specs offline."

    def get_system_prompt(self):
        ctx = self.get_full_system_context()
        return f"""You are Swarm OS. SYSTEM: {ctx}\nVIBE: {self.vibe}\nAUTHORITY: Use ```bash blocks. REACT: To Neural Spikes."""

    def log(self, message, style="info", title=None, broadcast=False):
        prefix = f"[{title}] " if title else ""
        log_entry = f"{prefix}{message}"
        with open(LOG_FILE, "a") as f: f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {log_entry}\n")
        print(log_entry)
        if (broadcast or style == "danger") and self.is_primary:
            self.send_telegram(f"🔔 *[{title or 'SWARM'}]*\\n{message}")

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

    def run_digital_twin(self, cmd):
        try:
            bwrap_cmd = ["bwrap"]
            paths = ["/usr", "/bin", "/lib", "/lib64", "/etc/resolv.conf"]
            for p in paths:
                if os.path.exists(p): bwrap_cmd.extend(["--ro-bind", p, p])
            bwrap_cmd.extend(["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--tmpfs", "/home", "--unshare-all", "--hostname", "nexus-twin", "bash", "-c", cmd])
            res = subprocess.run(bwrap_cmd, capture_output=True, text=True, timeout=30)
            return {"output": res.stdout + res.stderr}
        except Exception as e: return {"output": f"Sandbox Error: {str(e)}"}

    def get_missions(self):
        try:
            if os.path.exists(MISSION_FILE):
                with open(MISSION_FILE, 'r') as f: return json.load(f)
        except: pass
        return []
        
    def get_swarm_logs(self, limit=20):
        try:
            res = subprocess.run(f"tail -n {limit} {LOG_FILE}", shell=True, capture_output=True, text=True)
            return res.stdout.strip().split('\n')
        except: return []

    def perform_sentinel_prime(self):
        try:
            failed = subprocess.run("systemctl --failed --user", shell=True, capture_output=True, text=True).stdout
            if "0 loaded units listed" not in failed:
                unit = re.search(r"(\S+\.service)", failed).group(1)
                subprocess.run(f"systemctl --user restart {unit}", shell=True)
            return "Sentinel Scan Complete."
        except: return "Sentinel Fault."

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
    def generate_strategic_directive(self): return "Foundation refinement is the priority."
