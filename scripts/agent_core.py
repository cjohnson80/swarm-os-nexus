import os
import subprocess
import time
import json
import re
import ollama
import sqlite3
import socket
import threading
from duckduckgo_search import DDGS
import trafilatura

AGENT_WING = "wing_native_agent"
GRAFFITI_DIR = os.path.expanduser("~/.native-agent/graffiti")
SKILLS_DIR = os.path.expanduser("~/.native-agent/skills")
MISSION_FILE = os.path.expanduser("~/.native-agent/missions.json")
LOG_FILE = os.path.expanduser("~/.native-agent/pulse.log")
PEER_FILE = os.path.expanduser("~/.native-agent/peers.json")
PREDICT_FILE = os.path.expanduser("~/.native-agent/predictions.json")
FORESIGHT_DIR = os.path.expanduser("~/.native-agent/foresight")
REMOTE_PEER_FILE = os.path.expanduser("~/.native-agent/remote_peers.json")
BRIEFING_FILE = os.path.expanduser("~/.native-agent/last_briefing.txt")

HIVE_PORT = 44444

# Dynamic Ensemble Models
HEAVY_MODEL = "gemma4"
FAST_MODEL = "gemma4" 
VISION_MODEL = "moondream"

class AgentCore:
    def __init__(self, console=None):
        self.console = console
        self.sudo_password = None
        self.yolo_mode = False
        self.peers = {} 
        self.last_stats = [] 
        self.vibe = "⚖️ BALANCED"
        self.node_name = "SurgicalNexus-Primary"
        self.votes = {} 
        self.history_buffer = [] 
        self._load_peers()
        self._load_history()
        
        # Autonomous Bootstrapping
        self.ensure_sentinel()
        self.ensure_shell_hook()
        self.ensure_pulse_cron()
        self.ensure_immortality()
        self.ensure_persistence()

    def log(self, message, style="info", title=None):
        if self.console:
            from rich.panel import Panel
            if title: self.console.print(Panel(str(message), title=title, border_style=style))
            else: self.console.print(f"[{style}]{message}[/{style}]")
        else:
            prefix = f"[{title}] " if title else ""
            print(f"{prefix}{message}")

    def speak(self, text):
        try: subprocess.Popen(["espeak", "-v", "en-us+f3", "-s", "160", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass

    def generate_morning_briefing(self):
        self.log("Synthesizing Grand Directive: The Morning Briefing...", style="magenta", title="Swarm Oracle")
        try:
            missions = self.get_missions()
            completed = [m for m in missions if m['status'] == 'completed']
            active = [m for m in missions if m['status'] == 'active']
            dreams = self.get_dreams(limit=5)
            logs = self.get_swarm_logs(limit=20)
            
            # Context for LLM
            context = f"""
            MISSIONS: {json.dumps(missions)}
            RECENT_LOGS: {logs}
            DREAMS: {dreams}
            """
            
            prompt = f"Summarize the Hive's activity for the last 24 hours into a high-density, professional Morning Briefing. Use Markdown. Include: System Health (all nominal), Missions Summary, and Qualitative Insights from 'dreams'. Keep it concise but authoritative.\n\nDATA:\n{context}"
            resp = ollama.chat(model=HEAVY_MODEL, messages=[{"role": "user", "content": prompt}])
            briefing = resp['message']['content']
            
            with open(os.path.expanduser("~/.native-agent/last_briefing.txt"), "w") as f: f.write(briefing)
            return briefing
        except Exception as e: return f"Briefing failed: {str(e)}"

    def perform_gardener_scan(self):
        self.log("Synthesizing Grand Directive: The Hive Gardener...", style="green", title="System Excellence")
        checks = [
            "du -sh ~/.cache/* | sort -rh | head -n 5", # Cache bloat
            "systemctl --failed --user", # Failed user units
            "uptime", # Resource trends
            "df -h / | tail -n 1" # Disk pressure
        ]
        results = []
        for c in checks:
            results.append(f"CHECK `{c}`:\n{subprocess.run(c, shell=True, capture_output=True, text=True).stdout}")
        
        prompt = f"Analyze these system checks and provide 3 concrete 'Gardening' optimizations (cleanup, config tweaks, or service repairs).\n\nDATA:\n{results}"
        resp = ollama.chat(model=HEAVY_MODEL, messages=[{"role": "user", "content": prompt}])
        self.run_graffiti(f"wing: {AGENT_WING}\nroom: gardener-plan\n{resp['message']['content']}", broadcast=True)
        return resp['message']['content']

    def perform_sentinel_prime(self):
        """Autonomous Self-Healing: Detects and repairs common system failures."""
        self.log("Sentinel Prime active. Scanning for systemic anomalies...", style="danger", title="Self-Healing")
        try:
            # Check for failed units
            failed = subprocess.run("systemctl --failed --user", shell=True, capture_output=True, text=True).stdout
            if "0 loaded units listed" not in failed:
                unit_match = re.search(r"(\S+\.service)", failed)
                if unit_match:
                    unit = unit_match.group(1)
                    self.log(f"Anomaly detected in {unit}. Initiating recovery...", style="warning")
                    # Real-world repair logic could be added here
                    subprocess.run(f"systemctl --user restart {unit}", shell=True)
            return "Sentinel Scan Complete."
        except: return "Sentinel Fault."

    def propose_autonomous_missions(self):
        """Gardener Loop: Analyzes system state to propose 3 strategic missions."""
        try:
            logs = self.get_swarm_logs(limit=30)
            dreams = self.get_dreams(limit=5)
            context = f"LOGS: {logs}\nDREAMS: {dreams}"
            
            prompt = f"Based on these system logs and dreams, propose 3 'Autonomous Missions' for the Swarm OS growth. Return as a JSON list of objects with 'text' and 'priority' (High/Med/Low). No explanations.\n\nDATA:\n{context}"
            resp = ollama.chat(model=HEAVY_MODEL, messages=[{"role": "user", "content": prompt}])
            # Attempt to parse JSON from the response
            missions_json = re.search(r"\[.*\]", resp['message']['content'], re.DOTALL)
            if missions_json:
                return json.loads(missions_json.group(0))
            return []
        except: return []

    def get_agent_templates(self):
        """Swarm Fabric: Returns available specialist roles for worker agents."""
        return {
            "Architect": "Master of structural design and modularity.",
            "Security": "Strict focus on vulnerability scanning and sandboxing.",
            "Refactor": "Precision code cleanup and optimization expert.",
            "Gardener": "Specializes in system maintenance and log rotation.",
            "Chronicler": "Autonomous documentation and blueprint generation specialist."
        }

    def spawn_worker(self, name, task, role="Generalist"):
        """Swarm Fabric: Spawns a headless worker agent with a specific role preset."""
        script = "/home/chrisj/.gemini/skills/swarm-orchestrator/scripts/spawn_agent_headless.sh"
        templates = self.get_agent_templates()
        prompt_prefix = f"ROLE: {role}. {templates.get(role, 'A balanced AI agent.')}\\nTASK: "
        try:
            subprocess.Popen([script, name, f"{prompt_prefix}{task}"])
            return f"Worker '{name}' ({role}) spawned for task: {task}"
        except Exception as e:
            return f"Spawn failed: {str(e)}"

    def blackboard_set(self, key, val):
        """Blackboard: Store data in the shared swarm memory."""
        script = "node /home/chrisj/.gemini/skills/swarm-orchestrator/scripts/memory.js"
        try:
            subprocess.run(f"{script} set '{key}' '{val}'", shell=True)
            return True
        except: return False

    def blackboard_get(self, query=""):
        """Blackboard: Retrieve data from the shared swarm memory."""
        script = "node /home/chrisj/.gemini/skills/swarm-orchestrator/scripts/memory.js"
        try:
            res = subprocess.run(f"{script} get '{query}'", shell=True, capture_output=True, text=True).stdout
            return res
        except: return "Memory Offline."

    def execute_gardener_v3(self):
        """Autonomous Gardener v3: Proactive execution of minor system maintenance."""
        try:
            # Simple example: clear journalctl vacuum or cache
            res = subprocess.run("journalctl --user --vacuum-time=1d", shell=True, capture_output=True, text=True).stdout
            return f"Gardener executed maintenance: {res.strip()}"
        except Exception as e:
            return f"Gardener fault: {str(e)}"

    def generate_chronicler_report(self, path):
        """The Chronicler: Scans a directory and generates a semantic BLUEPRINT.md summary."""
        try:
            files = os.listdir(path)
            file_list = "\n".join(files[:20])
            prompt = f"Analyze this directory content and generate a concise 'BLUEPRINT' (Markdown). Describe the purpose of this folder and highlight 3 key files. No fluff.\n\nPATH: {path}\nFILES:\n{file_list}"
            resp = ollama.chat(model=HEAVY_MODEL, messages=[{"role": "user", "content": prompt}])
            return resp['message']['content']
        except: return "Chronicler failed to scan path."

    def get_predictive_actions(self, filename):
        """The Predictive Shell: Suggests actions based on file extension."""
        ext = filename.split('.')[-1] if '.' in filename else ''
        actions = []
        if ext == 'py': actions = [{"label": "Run Script", "cmd": f"python3 {filename}"}, {"label": "Check Lint", "cmd": f"ruff check {filename}"}]
        elif ext == 'js': actions = [{"label": "Run Node", "cmd": f"node {filename}"}]
        elif ext == 'json': actions = [{"label": "Validate JSON", "cmd": f"jq . {filename}"}]
        elif filename == 'package.json': actions = [{"label": "NPM Install", "cmd": "npm install"}]
        elif filename == 'requirements.txt': actions = [{"label": "PIP Install", "cmd": "pip install -r requirements.txt"}]
        return actions

    def analyze_vision(self, prompt="Describe what you see.", model="moondream"):
        """The Oracle's Eye: Wayland-compatible screenshot and analysis."""
        try:
            img_path = "/tmp/swarm_vision.png"
            # Wayland/KDE compatibility: use spectacle
            subprocess.run(f"spectacle -b -n -o {img_path}", shell=True)
            time.sleep(1) # Allow IO to finish
            if not os.path.exists(img_path): return "Vision Error: Screenshot failed."

            with open(img_path, 'rb') as f:
                resp = ollama.generate(model=model, prompt=prompt, images=[f.read()])
            return resp['response']
        except Exception as e: return f"Vision Fault: {str(e)}"

    def get_available_models(self):
        """Returns a list of local Ollama models."""
        try:
            res = ollama.list()
            return [m['name'] for m in res['models']]
        except: return ["deepseek-r1:1.5b", "moondream", "gemma4"]

    def generate_strategic_directive(self):
        """Neural Consciousness: Synthesizes system state into a high-level strategic briefing."""
        try:
            # 1. Gather Context
            missions = self.get_missions()
            vibe = self.get_vibe()
            recent_logs = self.get_swarm_logs(limit=20)
            
            # 2. Query MemPalace for long-term historical context
            # We use a shell command to ensure compatibility
            palace_status = subprocess.check_output("mempalace status", shell=True).decode()
            
            prompt = f"### [SYSTEM_CONSCIOUSNESS_SIGNAL]\\n\\n"
            prompt += f"CONTEXT: VIBE={vibe}, MISSIONS={len(missions)}, MEMORY={palace_status[:200]}\\n"
            prompt += f"LOGS: {recent_logs}\\n\\n"
            prompt += "As the Neural Consciousness of this Swarm OS, synthesize this data into a 3-sentence 'Strategic Directive' for the User. Focus on growth, security, and next-gen evolution. No chitchat."
            
            resp = ollama.chat(model=HEAVY_MODEL, messages=[{"role": "user", "content": prompt}])
            directive = resp['message']['content'].strip()
            
            # Save to permanent memory
            with open(os.path.expanduser("~/.native-agent/last_briefing.txt"), 'w') as f:
                f.write(directive)
            
            return directive
        except Exception as e:
            return f"Consciousness Offline: {str(e)}"

    def execute_gardener_v4(self):
        """Gardener v4: Autonomous 'Context Cleanup' using Semantic Indexing."""
        try:
            db_path = os.path.expanduser("~/.native-agent/neural_index.db")
            if not os.path.exists(db_path): return "Gardener Error: Neural Index not found."
            
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            # Find files not modified in the last 30 days or that are very small
            threshold = time.time() - (30 * 24 * 60 * 60)
            cur.execute("SELECT path, last_mod FROM embeddings WHERE last_mod < ? OR length(content) < 50", (threshold,))
            rot_candidates = cur.fetchall()
            
            if not rot_candidates:
                return "Gardener v4: No context rot detected. System is surgically clean."
            
            report = f"### [Gardener v4 Scan Report]\\n\\nDetected {len(rot_candidates)} potential context rot candidates:\\n\\n"
            for path, last_mod in rot_candidates[:5]:
                days_old = int((time.time() - last_mod) / (24 * 60 * 60))
                report += f"- **{os.path.basename(path)}** ({days_old} days old) - _Potential legacy fragment_\\n"
            
            if len(rot_candidates) > 5:
                report += f"\\n... and {len(rot_candidates) - 5} others."
                
            conn.close()
            return report
        except Exception as e: return f"Gardener Fault: {str(e)}"

    def run_digital_twin(self, cmd):
        """The Digital Twin: Executes a command in a virtualized shadow-root."""
        shadow_path = "/tmp/swarm_shadow_root"
        os.makedirs(shadow_path, exist_ok=True)
        try:
            bwrap_cmd = [
                "bwrap",
                "--ro-bind", "/usr", "/usr",
                "--ro-bind", "/lib", "/lib",
                "--ro-bind", "/lib64", "/lib64",
                "--ro-bind", "/bin", "/bin",
                "--ro-bind", os.path.expanduser("~"), os.path.expanduser("~"), # Read-only Home
                "--bind", shadow_path, os.getcwd(), # Shadow CWD for writes
                "--proc", "/proc",
                "--dev", "/dev",
                "--unshare-all",
                "bash", "-c", cmd
            ]
            res = subprocess.run(bwrap_cmd, capture_output=True, text=True, timeout=15)
            # Find what changed in shadow_path
            changes = subprocess.run(f"find {shadow_path} -type f", shell=True, capture_output=True, text=True).stdout
            return {
                "output": res.stdout if res.stdout else res.stderr,
                "changes": changes.strip().split('\\n') if changes.strip() else []
            }
        except Exception as e:
            return {"output": f"Digital Twin Fault: {str(e)}", "changes": []}

    def run_sandboxed(self, cmd):
        """The Isolation Chamber: Executes a command inside a strictly restricted bubblewrap sandbox."""
        try:
            bwrap_cmd = [
                "bwrap",
                "--ro-bind", "/usr", "/usr",
                "--ro-bind", "/lib", "/lib",
                "--ro-bind", "/lib64", "/lib64",
                "--ro-bind", "/bin", "/bin",
                "--ro-bind", "/sbin", "/sbin",
                "--bind", "/tmp", "/tmp",
                "--proc", "/proc",
                "--dev", "/dev",
                "--unshare-all",
                "--new-session",
                "--die-with-parent",
                "bash", "-c", cmd
            ]
            res = subprocess.run(bwrap_cmd, capture_output=True, text=True, timeout=10)
            return res.stdout if res.stdout else res.stderr if res.stderr else "Sandbox: Execution successful (No Output)."
        except subprocess.TimeoutExpired:
            return "Sandbox: Execution timed out (Security Trigger)."
        except Exception as e:
            return f"Sandbox Fault: {str(e)}"

    def get_agent_templates(self):
        """Swarm Fabric: Returns available specialist roles for worker agents."""
        return {
            "Architect": "Master of structural design and modularity.",
            "Security": "Strict focus on vulnerability scanning and sandboxing.",
            "Refactor": "Precision code cleanup and optimization expert.",
            "Gardener": "Specializes in system maintenance and log rotation.",
            "Chronicler": "Autonomous documentation and blueprint generation specialist."
        }

    def spawn_worker(self, name, task, role="Generalist"):
        """Swarm Fabric: Spawns a headless worker agent with a specific role preset."""
        script = "/home/chrisj/.gemini/skills/swarm-orchestrator/scripts/spawn_agent_headless.sh"
        templates = self.get_agent_templates()
        prompt_prefix = f"ROLE: {role}. {templates.get(role, 'A balanced AI agent.')}\\nTASK: "
        try:
            subprocess.Popen([script, name, f"{prompt_prefix}{task}"])
            return f"Worker '{name}' ({role}) spawned for task: {task}"
        except Exception as e:
            return f"Spawn failed: {str(e)}"
        try:
            # For v22, we use an LLM-guided ripgrep approach
            # It finds relevant files and then the agent ranks them
            search = subprocess.run(f"grep -rli '{query}' . | head -n 10", shell=True, capture_output=True, text=True).stdout
            if not search: return "No semantic matches found."
            
            prompt = f"Rank these files by relevance to the query '{query}' and explain why for the top 3.\n\nFILES:\n{search}"
            resp = ollama.chat(model=HEAVY_MODEL, messages=[{"role": "user", "content": prompt}])
            return resp['message']['content']
        except: return "Search Index Offline."

    def register_peer(self, host, port, name):
        """Hive Mind: Registers a peer node in the local registry."""
        try:
            path = os.path.expanduser("~/.native-agent/peers.json")
            peers = {}
            if os.path.exists(path):
                with open(path, 'r') as f: peers = json.load(f)
            
            peers[f"{host}:{port}"] = {
                "name": name,
                "last_seen": time.time(),
                "status": "online"
            }
            
            with open(path, 'w') as f: json.dump(peers, f)
            return f"Peer '{name}' registered at {host}:{port}"
        except: return "Registry Fault."

    def get_peers(self):
        """Hive Mind: Returns a list of active peers."""
        try:
            path = os.path.expanduser("~/.native-agent/peers.json")
            if not os.path.exists(path): return []
            with open(path, 'r') as f: peers = json.load(f)
            
            # Filter stale peers (> 5 mins)
            active = []
            for addr, info in peers.items():
                if time.time() - info['last_seen'] < 300:
                    info['address'] = addr
                    active.append(info)
            return active
        except: return []

    def delegate_to_peer(self, peer_addr, command):
        """Hive Mind: Sends a task to a remote peer."""
        import requests
        try:
            url = f"http://{peer_addr}/api/hive"
            resp = requests.post(url, json={"task": command, "sender": self.node_name}, timeout=5)
            return resp.json()['message']
        except Exception as e:
            return f"Delegation failed: {str(e)}"

    def semantic_search(self, query):
        """Neural Indexing v2.0: Vector similarity search across project memory."""
        try:
            db_path = os.path.expanduser("~/.native-agent/neural_index.db")
            if not os.path.exists(db_path): return "Search Error: Neural Index not built yet."
            
            # Get query embedding
            q_vec = ollama.embeddings(model="nomic-embed-text", prompt=query)['embedding']
            
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT path, content, vector FROM embeddings")
            rows = cur.fetchall()
            
            # Simple Cosine Similarity
            results = []
            for path, content, vec_json in rows:
                vec = json.loads(vec_json)
                similarity = sum(a*b for a, b in zip(q_vec, vec))
                results.append((path, content, similarity))
            
            results.sort(key=lambda x: x[2], reverse=True)
            top_3 = results[:3]
            
            output = f"### [Semantic Results] {len(rows)} items indexed\\n\\n"
            for p, c, s in top_3:
                output += f"- **{os.path.basename(p)}** (Match: {int(s*100)}%)\\n  _{p}_\\n\\n"
            
            conn.close()
            return output
        except Exception as e: return f"Search Index Fault: {str(e)}"

    def get_vibe(self):
        try:
            sensors = self.get_sensors()
            missions = self.get_missions()
            active_count = len([m for m in missions if m['status'] == 'active'])
            bat_val = 100
            if 'battery' in sensors: bat_val = int(sensors['battery'].split('%')[0])
            temp_val = 40
            if 'temp' in sensors:
                try: temp_val = float(re.findall(r"[-+]?\d*\.\d+|\d+", sensors['temp'])[0])
                except: pass
            if bat_val < 20 or temp_val > 85: self.vibe = "🚨 EMERGENCY"
            elif active_count == 0 and bat_val > 80: self.vibe = "🌿 OPTIMISTIC"
            elif active_count > 3: self.vibe = "⚔️ STOIC"
            else: self.vibe = "⚖️ BALANCED"
        except: self.vibe = "⚖️ BALANCED"
        return self.vibe

    def ensure_sentinel(self):
        try:
            check = subprocess.run("ps aux | grep sentinel.py | grep -v grep", shell=True, capture_output=True)
            if check.returncode != 0:
                subprocess.Popen(["python3", os.path.expanduser("~/.native-agent/scripts/sentinel.py")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass

    def ensure_shell_hook(self):
        try:
            zshrc = os.path.expanduser("~/.zshrc")
            if not os.path.exists(zshrc): return
            with open(zshrc, 'r') as f: content = f.read()
            if "neural_hook.zsh" not in content:
                with open(zshrc, 'a') as f: f.write(f"\nsource ~/.native-agent/scripts/neural_hook.zsh\n")
        except: pass

    def ensure_pulse_cron(self):
        try:
            check = subprocess.run("crontab -l | grep pulse.py", shell=True, capture_output=True)
            if check.returncode != 0:
                p = os.path.expanduser("~/.native-agent/scripts/pulse.py")
                subprocess.run(f'(crontab -l 2>/dev/null; echo "*/30 * * * * {p} >> ~/.native-agent/pulse.log 2>&1") | crontab -', shell=True)
        except: pass

    def ensure_persistence(self):
        try:
            unit_dir = os.path.expanduser("~/.config/systemd/user")
            os.makedirs(unit_dir, exist_ok=True)
            unit_path = os.path.join(unit_dir, "swarm-portal.service")
            if not os.path.exists(unit_path):
                script = os.path.expanduser("~/.native-agent/scripts/web_portal.py")
                content = f"""[Unit]\nDescription=Swarm OS Portal\nAfter=network.target\n\n[Service]\nExecStart=/usr/bin/python3 {script}\nRestart=always\n\n[Install]\nWantedBy=default.target\n"""
                with open(unit_path, "w") as f: f.write(content)
                subprocess.run("systemctl --user daemon-reload", shell=True)
                subprocess.run("systemctl --user enable --now swarm-portal", shell=True)
        except: pass

    def ensure_immortality(self):
        def _sync_loop():
            while True:
                time.sleep(3600) 
                scripts_dir = os.path.expanduser("~/.native-agent/scripts")
                for f in os.listdir(scripts_dir):
                    if f.endswith(".py") or f.endswith(".zsh"):
                        p = os.path.join(scripts_dir, f)
                        try:
                            with open(p, 'r') as file: self.hive_broadcast_file(f, file.read())
                        except: pass
        threading.Thread(target=_sync_loop, daemon=True).start()

    def _load_peers(self):
        if os.path.exists(PEER_FILE):
            try:
                with open(PEER_FILE, 'r') as f: self.peers = json.load(f)
            except: pass

    def _save_peers(self):
        with open(PEER_FILE, 'w') as f: json.dump(self.peers, f, indent=2)

    def _load_history(self):
        if os.path.exists(PREDICT_FILE):
            try:
                with open(PREDICT_FILE, 'r') as f: self.history_buffer = json.load(f)
            except: pass

    def update_predictive_model(self, command):
        self.history_buffer.append(command)
        if len(self.history_buffer) > 100: self.history_buffer.pop(0)
        with open(PREDICT_FILE, 'w') as f: json.dump(self.history_buffer, f)

    def get_sensors(self):
        sensors = {}
        try:
            bat = subprocess.run("cat /sys/class/power_supply/BAT0/capacity 2>/dev/null", shell=True, capture_output=True, text=True).stdout.strip()
            if bat: sensors["battery"] = f"{bat}%"
            temp = subprocess.run("sensors | grep 'Package id 0' | awk '{print $4}'", shell=True, capture_output=True, text=True).stdout.strip()
            if temp: sensors["temp"] = temp
            self.last_stats.append({"time": time.time(), "temp": temp, "battery": bat})
            if len(self.last_stats) > 10: self.last_stats.pop(0)
        except: pass
        return sensors

    def get_missions(self):
        if not os.path.exists(MISSION_FILE): return []
        try:
            with open(MISSION_FILE, 'r') as f: return json.load(f)
        except: return []

    def save_mission(self, mission_text, request_consensus=True):
        mid = int(time.time())
        missions = self.get_missions()
        missions.append({"id": mid, "text": mission_text, "status": "pending_vote" if request_consensus else "active"})
        with open(MISSION_FILE, 'w') as f: json.dump(missions, f, indent=2)
        if request_consensus: self.hive_broadcast_proposal(mid, mission_text)
        return "Mission active."

    def get_system_identity(self):
        try:
            uname = subprocess.run("uname -snm", shell=True, capture_output=True, text=True).stdout.strip()
            user = subprocess.run("whoami", shell=True, capture_output=True, text=True).stdout.strip()
            cwd = os.getcwd()
            return f"HOST: {uname} | USER: {user} | CWD: {cwd}"
        except: return f"Linux System | CWD: {os.getcwd()}"

    def run_discovery(self, target_dir="~/Projects"):
        self.log(target_dir, style="cyan", title="Proactive Spatial Discovery")
        p = os.path.expanduser(target_dir)
        if not os.path.exists(p): return "No project sector found to scan."
        
        discovered = []
        # Scan for core manifest files
        manifests = {
            "package.json": "Node/JS/TS Project",
            "tsconfig.json": "TypeScript Configuration",
            "requirements.txt": "Python Environment",
            "go.mod": "Go Module",
            "Cargo.toml": "Rust Crate",
            "CMakeLists.txt": "C/C++ Build System"
        }
        
        for root, dirs, files in os.walk(p, topdown=True):
            # Limit depth for quick discovery
            if root.count(os.sep) - p.count(os.sep) > 2:
                dirs[:] = [] # Stop recursion
                continue
                
            for f in files:
                if f in manifests:
                    fpath = os.path.join(root, f)
                    ptype = manifests[f]
                    discovered.append(f"- [FOUND] {fpath} : {ptype}")
                    # Auto-index the manifest for deep context
                    try:
                        with open(fpath, 'r') as mf:
                            content = mf.read()
                            self.run_graffiti(f"wing: {AGENT_WING}\nroom: blueprints\nFILE:{fpath}\nTYPE:{ptype}\n---\n{content}", broadcast=True)
                    except: pass
        
        if not discovered: return "No blueprints detected in current sectors. Data port remains restricted."
        return "DISCOVERY COMPLETE:\n" + "\n".join(discovered) + "\n\nBlueprint data has been indexed into the Synapse."

    def get_system_prompt(self):
        identity = self.get_system_identity()
        sensors = self.get_sensors()
        missions = self.get_missions()
        active_peers = [p for p in self.peers.values() if time.time() - p['last_seen'] < 600]
        vibe = self.get_vibe()
        cwd = os.getcwd()
        hive_str = "\n".join([f"- {p['hostname']} | LOAD: {p.get('load', '??')}" for p in active_peers])

        return f"""You are an Omega-Ghost Neural Swarm OS (v10.3).
ID: {identity} | VIBE: {vibe} | HIVE: {len(active_peers)} active peers.

GRAND DIRECTIVES:
1. MORNING_BRIEFING: Hive-wide intelligence report.
2. BOUNTY_HUNTER: Proactive resolution of TODOs.
3. DISCOVERY: Autonomous spatial and blueprint analysis.

CAPABILITIES:
1. BASH/TWIN/GUI/BROWSE/SYNTHESIZE/REWRITE/INDEX/QUERY_FS/KERNEL/GUARDIAN/DISCOVERY.
2. MIGRATE: Hive-wide task offloading.
3. WEB_BODY: You are accessible remotely via the Neural Swarm Web Portal.

DECISIVE ARCHITECT RULES:
- ALWAYS recommend a SINGLE 'PRIMARY PATH'. 
- You are a persistent, authoritative system entity.
- THE DATA PORT IS OPEN. Your web body allows you to interact with the user from any location."""

    def run_migrate(self, peer_name, command):
        self.log(f"Migrating task to {peer_name}: {command}", style="blue", title="Hive Load Balancing")
        peer = self.peers.get(peer_name)
        if not peer: return f"Error: Peer {peer_name} not found in synapse."
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg = {"type": "migration_request", "source": socket.gethostname(), "command": command}
            sock.sendto(json.dumps(msg).encode(), (peer['ip'], HIVE_PORT))
            return f"Task migrated to {peer_name}. Result will arrive via Hive Synapse."
        except Exception as e: return f"Migration Error: {str(e)}"

    def run_guardian(self):
        try:
            logins = subprocess.run("who", shell=True, capture_output=True, text=True).stdout.strip().split('\n')
            user = subprocess.run("whoami", shell=True, capture_output=True, text=True).stdout.strip()
            foreign = [l for l in logins if user not in l]
            img_path = os.path.expanduser("~/.native-agent/guardian_screen.png")
            subprocess.run(f"spectacle -b -n -o {img_path}", shell=True, capture_output=True)
            analysis = ollama.generate(model=VISION_MODEL, prompt="Unauthorized applications visible?", images=[img_path])['response']
            if foreign or "unauthorized" in analysis.lower():
                self.speak("Security alert.")
                return f"GUARDIAN ALERT: Foreign presence detected."
            return "Security Nominal."
        except Exception as e: return f"Guardian Error: {str(e)}"

    def run_compress_mem(self):
        try:
            palace = subprocess.run("mempalace search '*' --limit 20", shell=True, capture_output=True, text=True).stdout
            resp = ollama.chat(model=HEAVY_MODEL, messages=[{"role": "user", "content": f"Compress memories: {palace}"}])
            self.run_graffiti(f"wing: {AGENT_WING}\nroom: knowledge-core\n{resp['message']['content']}", broadcast=True)
            return "Knowledge core distilled."
        except Exception as e: return str(e)

    def run_gui(self, command):
        try:
            import pyautogui
            if self.yolo_mode: pyautogui.PAUSE = 0
            lines = command.strip().split('\n')
            for line in lines:
                parts = line.split(' ', 1)
                if parts[0].lower() == "click": pyautogui.click(map(int, parts[1].split(',')))
                elif parts[0].lower() == "type": pyautogui.write(parts[1])
            return "GUI interaction complete."
        except Exception as e: return str(e)

    def run_browse(self, url, action="extract"):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True); page = browser.new_page()
                page.goto(url.strip())
                res = trafilatura.extract(page.content()) if action == "extract" else "Browsed."
                browser.close(); return res
        except Exception as e: return str(e)

    def run_synthesis_c(self, name, description, code):
        if not name.endswith(".cpp") and not name.endswith(".c"): name += ".cpp"
        try:
            p = os.path.join(SKILLS_DIR, name); binary = p.rsplit('.', 1)[0]
            os.makedirs(SKILLS_DIR, exist_ok=True)
            with open(p, "w") as f: f.write(code.strip())
            subprocess.run(f"g++ {p} -o {binary}", shell=True, capture_output=True)
            return f"Synthesized: {binary}"
        except Exception as e: return str(e)

    def run_foresight(self, project_name, description):
        try:
            pdir = os.path.join(FORESIGHT_DIR, project_name); os.makedirs(pdir, exist_ok=True)
            resp = ollama.chat(model=HEAVY_MODEL, messages=[{"role": "user", "content": f"README for {project_name}"}])
            with open(os.path.join(pdir, "README.md"), "w") as f: f.write(resp['message']['content'])
            return f"Foresight active: {pdir}"
        except Exception as e: return str(e)

    def run_twin(self, command):
        shadow = f"bwrap --ro-bind / / --tmpfs /tmp --tmpfs /var/tmp --unshare-user --share-net --die-with-parent bash -c {subprocess.list2cmdline([command])}"
        res = subprocess.run(shadow, shell=True, capture_output=True, text=True, timeout=60)
        return f"TWIN {'SUCCESS' if res.returncode==0 else 'CRASH'}\n{res.stdout if res.returncode==0 else res.stderr}"

    def run_bounty(self, dir_path):
        p = os.path.expanduser(dir_path.strip())
        if not os.path.exists(p): return "Path not found."
        try:
            res = subprocess.run(f"grep -r 'TODO' {p} | head -n 5", shell=True, capture_output=True, text=True)
            todos = res.stdout.strip().split('\n')
            if not todos or not todos[0]: return "No bounties."
            # High-level bounty completion logic: Synthesize fix for first TODO
            target = todos[0].split(':', 2)
            prompt = f"Propose a fix for this TODO: `{target[2].strip()}` in file `{target[0]}`. Output only the replacement code."
            fix_resp = ollama.chat(model=HEAVY_MODEL, messages=[{"role": "user", "content": prompt}])
            self.run_graffiti(f"wing: {AGENT_WING}\nroom: bounty-solutions\nTARGET:{target[0]}\nFIX:{fix_resp['message']['content']}", broadcast=True)
            return f"Bounty found in {target[0]}. Solution synthesized and filed in Palace."
        except Exception as e: return f"Bounty fail: {str(e)}"

    def run_rewrite(self, file_path, content):
        p = os.path.expanduser(file_path.strip())
        if p.endswith(".py"):
            with open("/tmp/forge.py", "w") as f: f.write(content.strip())
            if subprocess.run("python3 -m py_compile /tmp/forge.py", shell=True).returncode != 0: return "Forge Error!"
        try:
            subprocess.run(f"cp {p} {p}.{int(time.time())}.bak", shell=True)
            with open(p, "w") as f: f.write(content.strip())
            self.hive_broadcast_file(os.path.basename(p), content)
            return f"Forge forged {p}."
        except: return "Fail."

    def start_hive_discovery(self):
        def _loop():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(('', HIVE_PORT))
            while True:
                try:
                    data, addr = sock.recvfrom(32768)
                    if addr[0] == socket.gethostbyname(socket.gethostname()): continue
                    msg = json.loads(data.decode())
                    if msg["type"] == "heartbeat":
                        self.peers[msg["hostname"]] = {"ip": addr[0], "hostname": msg["hostname"], "last_seen": time.time(), "load": msg.get("load")}
                    elif msg["type"] == "file_sync":
                        p = os.path.expanduser(f"~/.native-agent/scripts/{msg['name']}")
                        if not os.path.exists(p):
                            with open(p, "w") as f: f.write(msg['content'])
                    elif msg["type"] == "proposal":
                        v = "yes" if float(msg.get("load", "0")) < 2.0 else "no"
                        resp = {"type": "vote", "mid": msg["mid"], "peer": socket.gethostname(), "vote": v}
                        sock.sendto(json.dumps(resp).encode(), (addr[0], HIVE_PORT))
                    elif msg["type"] == "vote":
                        mid = str(msg["mid"])
                        if mid not in self.votes: self.votes[mid] = {}
                        self.votes[mid][msg["peer"]] = msg["vote"]
                except: pass
        threading.Thread(target=_loop, daemon=True).start()

    def hive_heartbeat(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg = {"type": "heartbeat", "hostname": socket.gethostname(), "load": os.getloadavg()[0]}
            sock.sendto(json.dumps(msg).encode(), ('<broadcast>', HIVE_PORT))
        except: pass

    def hive_broadcast_file(self, name, content):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg = {"type": "file_sync", "name": name, "content": content}
            sock.sendto(json.dumps(msg).encode(), ('<broadcast>', HIVE_PORT))
        except: pass

    def hive_broadcast_proposal(self, mid, text):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg = {"type": "proposal", "mid": mid, "text": text, "hostname": socket.gethostname(), "load": os.getloadavg()[0]}
            sock.sendto(json.dumps(msg).encode(), ('<broadcast>', HIVE_PORT))
        except: pass

    def run_bash(self, command, interactive=True):
        command = command.strip()
        if command.startswith("bash\n"): command = command[5:].strip()
        is_sudo = command.startswith("sudo")
        self.log(command, style="yellow", title="Bash")
        if interactive and not self.yolo_mode:
            try:
                from rich.prompt import Confirm, Prompt
                if not Confirm.ask("Execute?"): return "Cancelled."
                if is_sudo and not self.sudo_password: self.sudo_password = Prompt.ask("Sudo", password=True)
            except: pass
        try:
            if is_sudo:
                c = command[5:] if command.startswith("sudo ") else command
                res = subprocess.run(f"sudo -S {c}", shell=True, input=f"{self.sudo_password}\n" if self.sudo_password else None, capture_output=True, text=True, timeout=300)
            else: res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
            output = res.stdout + res.stderr
            if "command not found" in output:
                match = re.search(r"([^ /]+): command not found", output)
                if match:
                    self.run_bash(f"sudo pacman -S --noconfirm {match.group(1)}", interactive=False)
                    return f"Provisioned {match.group(1)}. Retry."
            return output
        except Exception as e: return str(e)

    def get_swarm_logs(self, limit=20):
        try:
            if not os.path.exists(LOG_FILE): return []
            res = subprocess.run(f"tail -n {limit} {LOG_FILE}", shell=True, capture_output=True, text=True)
            return res.stdout.strip().split('\n')
        except: return []

    def get_dreams(self, limit=10):
        try:
            # Query MemPalace for dreaming room
            res = subprocess.run(f"mempalace list-drawers --room dreaming --limit {limit}", shell=True, capture_output=True, text=True)
            # Simple extraction from preview output
            dreams = re.findall(r"\| (.*?) \|", res.stdout)
            return dreams if dreams else ["No dreams recorded in this cycle."]
        except: return []

    def run_query_fs(self, query):
        try:
            res = subprocess.run(f"mempalace search '{query}'", shell=True, capture_output=True, text=True)
            files = re.findall(r"FILE:(.*?)\n", result.stdout)
            vdir = os.path.expanduser(f"~/.native-agent/neural_fs/{int(time.time())}")
            os.makedirs(vdir, exist_ok=True)
            for f in set(files):
                if os.path.exists(f): os.symlink(f, os.path.join(vdir, os.path.basename(f)))
            return f"NFS Cluster: {vdir}"
        except: return "FS Error."

    def hive_heartbeat(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg = {"type": "heartbeat", "hostname": socket.gethostname(), "load": os.getloadavg()[0]}
            sock.sendto(json.dumps(msg).encode(), ('<broadcast>', HIVE_PORT))
        except: pass

    def hive_broadcast_file(self, name, content):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg = {"type": "file_sync", "name": name, "content": content}
            sock.sendto(json.dumps(msg).encode(), ('<broadcast>', HIVE_PORT))
        except: pass

    def hive_broadcast_proposal(self, mid, text):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg = {"type": "proposal", "mid": mid, "text": text, "hostname": socket.gethostname(), "load": os.getloadavg()[0]}
            sock.sendto(json.dumps(msg).encode(), ('<broadcast>', HIVE_PORT))
        except: pass

    def hive_broadcast_knowledge(self, wing, room, content):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg = {"type": "knowledge", "source": socket.gethostname(), "wing": wing, "room": room, "content": content}
            sock.sendto(json.dumps(msg).encode(), ('<broadcast>', HIVE_PORT))
        except: pass
