import eventlet
eventlet.monkey_patch()

import os
import json
import subprocess
import time
import re
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit
import ollama

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
from agent_core import AgentCore

app = Flask(__name__)
app.config['SECRET_KEY'] = 'swarm-secret-infinite'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

agent = AgentCore()
SESSION_MEMORIES = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS | SINGLE_STREAM_v34</title>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;500;700&family=Inter:wght@200;400;600;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #030303;
            --accent: #fff;
            --glass: rgba(255, 255, 255, 0.03);
            --glass-border: rgba(255, 255, 255, 0.08);
            --text-main: #fff;
            --text-dim: #888;
            --success: #00ffaa;
            --danger: #ff3333;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; outline: none; }
        body { 
            background: var(--bg); color: var(--text-main); font-family: 'Inter', sans-serif; 
            height: 100vh; overflow: hidden; display: flex; font-weight: 400;
        }

        #living-bg {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1;
            background: radial-gradient(circle at 50% 50%, #0a0a0a 0%, #000 100%);
        }
        #grid-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1;
            background-image: radial-gradient(var(--glass-border) 1px, transparent 1px);
            background-size: 40px 40px; opacity: 0.2;
        }

        /* Minimal Status HUD */
        #hud-top {
            position: fixed; top: 30px; left: 50%; transform: translateX(-50%); 
            display: flex; gap: 40px; z-index: 100;
        }
        .hud-item { display: flex; flex-direction: column; align-items: center; gap: 4px; }
        .hud-label { font-size: 8px; font-weight: 900; letter-spacing: 2px; color: var(--text-dim); }
        .hud-val { font-family: 'JetBrains Mono'; font-size: 11px; font-weight: 500; }

        /* Security Toggle */
        #lock-pill {
            position: fixed; bottom: 60px; left: 40px; width: 44px; height: 44px; 
            background: var(--glass); border: 1px solid var(--glass-border); border-radius: 50%;
            display: flex; align-items: center; justify-content: center; cursor: pointer;
            backdrop-filter: blur(10px); z-index: 100; opacity: 0.5; transition: 0.3s;
        }
        #lock-pill:hover { opacity: 1; border-color: var(--accent); }
        #lock-pill.active { border-color: var(--success); opacity: 1; box-shadow: 0 0 20px rgba(0,255,170,0.1); }

        /* Unified Stream Viewport */
        #app-viewport {
            flex: 1; display: flex; flex-direction: column; align-items: center;
            padding: 80px 30px 120px 30px; position: relative;
        }

        #neural-center {
            width: 100%; max-width: 850px; flex: 1; display: flex; flex-direction: column;
            overflow: hidden;
        }

        #chat-scroller { 
            flex: 1; overflow-y: auto; padding: 20px 5%; display: flex; flex-direction: column; gap: 50px;
            scroll-behavior: smooth;
        }

        /* Messages */
        .msg { opacity: 0; transform: translateY(15px); animation: msg-in 0.6s forwards cubic-bezier(0.16, 1, 0.3, 1); }
        @keyframes msg-in { to { opacity: 1; transform: translateY(0); } }

        .msg-label { font-size: 8px; font-weight: 900; letter-spacing: 4px; color: var(--text-dim); margin-bottom: 20px; display: block; }
        .user-msg .msg-label { color: var(--accent); }
        .autonomous-msg .msg-label { color: var(--success); }

        .msg-bubble { 
            font-size: 17px; line-height: 1.8; color: var(--text-main); font-weight: 200;
        }

        /* Code & Action */
        pre { background: #000; padding: 25px; border-radius: 12px; border: 1px solid var(--glass-border); margin: 25px 0; position: relative; overflow-x: auto; }
        code { font-family: 'JetBrains Mono'; color: var(--success); }
        .commit-btn {
            position: absolute; top: 15px; right: 15px; background: var(--success); color: #000;
            border: none; padding: 8px 16px; font-size: 9px; font-weight: 900; border-radius: 4px;
            cursor: pointer; transition: 0.3s;
        }

        /* Shadow-Entry Modal */
        #shadow-entry {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.8); backdrop-filter: blur(20px);
            display: none; align-items: center; justify-content: center; z-index: 2000;
        }
        .entry-card {
            background: var(--glass); border: 1px solid var(--glass-border); padding: 40px;
            border-radius: 20px; width: 100%; max-width: 400px; text-align: center;
        }
        .entry-card input {
            width: 100%; background: rgba(255,255,255,0.02); border: 1px solid var(--glass-border);
            padding: 15px; color: #fff; text-align: center; border-radius: 8px; margin-top: 20px;
            font-family: 'JetBrains Mono'; letter-spacing: 5px; font-size: 18px;
        }

        /* Input Dock */
        #input-nexus {
            position: fixed; bottom: 50px; left: 50%; transform: translateX(-50%);
            width: 100%; max-width: 700px; background: rgba(255,255,255,0.02);
            border: 1px solid var(--glass-border); border-radius: 30px; padding: 15px 30px;
            backdrop-filter: blur(20px); display: flex; align-items: center; gap: 20px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.5); z-index: 1000;
        }
        #cmd-input {
            flex: 1; background: transparent; border: none; color: #fff; font-size: 16px;
            font-family: inherit; font-weight: 200;
        }

        /* Live Ticker */
        #intel-ticker {
            position: fixed; bottom: 0; left: 0; width: 100%; height: 30px;
            background: #000; display: flex; align-items: center; padding: 0 30px;
            font-family: 'JetBrains Mono'; font-size: 9px; color: #444; border-top: 1px solid #111;
        }

        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-thumb { background: var(--glass-border); }
    </style>
</head>
<body>
    <div id="living-bg"></div>
    <div id="grid-overlay"></div>

    <div id="hud-top">
        <div class="hud-item">
            <span class="hud-label">SYNAPSE</span>
            <span id="cpu-val" class="hud-val">0.00</span>
        </div>
        <div class="hud-item">
            <span class="hud-label">RESERVE</span>
            <span id="ram-val" class="hud-val">0.0%</span>
        </div>
        <div class="hud-item">
            <span class="hud-label">TELEMETRY</span>
            <span id="cwd-val" class="hud-val">/home/chrisj</span>
        </div>
    </div>

    <div id="lock-pill" onclick="showShadowEntry()" title="Authorize Elevated Control">🔒</div>

    <div id="shadow-entry">
        <div class="entry-card">
            <span class="hud-label" style="font-size:10px;">AUTHORIZE_NEXUS_CORE</span>
            <input type="password" id="shadow-pw" placeholder="••••••••" autocomplete="off">
            <div style="margin-top:20px; font-size:9px; color:var(--text-dim); letter-spacing:1px;">ESC TO CANCEL | ENTER TO CONFIRM</div>
        </div>
    </div>

    <div id="app-viewport">
        <div id="neural-center">
            <div id="chat-scroller"></div>
        </div>
    </div>

    <div id="input-nexus">
        <div id="status-dot" style="width:6px; height:6px; border-radius:50%; background:var(--success); box-shadow:0 0 10px var(--success);"></div>
        <input type="text" id="cmd-input" placeholder="Type a message or command..." autocomplete="off">
    </div>

    <div id="intel-ticker">
        <span style="color:var(--success); margin-right:15px;">LIVE_PULSE</span>
        <div id="ticker-content">Nexus stream active...</div>
    </div>

    <script>
        const socket = io();
        const scroller = document.getElementById('chat-scroller');
        const input = document.getElementById('cmd-input');
        const ticker = document.getElementById('ticker-content');
        const statusDot = document.getElementById('status-dot');
        const shadowEntry = document.getElementById('shadow-entry');
        const shadowInput = document.getElementById('shadow-pw');

        function showShadowEntry() {
            shadowEntry.style.display = 'flex';
            shadowInput.focus();
        }

        shadowInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') shadowEntry.style.display = 'none';
            if (e.key === 'Enter') {
                const pw = shadowInput.value;
                if (pw) {
                    socket.emit('sudo_unlock', { password: pw });
                    document.getElementById('lock-pill').innerText = '🔓';
                    document.getElementById('lock-pill').classList.add('active');
                }
                shadowInput.value = '';
                shadowEntry.style.display = 'none';
            }
        });

        function dispatch() {
            const val = input.value.trim();
            if (!val) return;
            appendMsg('user', val);
            socket.emit('user_msg_stream', { content: val, model: 'gemma4' });
            input.value = '';
        }

        function appendMsg(role, content) {
            const div = document.createElement('div');
            div.className = `msg ${role}-msg`;
            const label = role === 'user' ? 'USER_SIGNAL' : (role === 'system_autonomous' ? 'SYSTEM_AUTONOMOUS' : 'AGENT_REASONING');
            
            div.innerHTML = `<span class="msg-label">${label}</span><div class="msg-bubble">${marked.parse(content)}</div>`;
            scroller.appendChild(div);
            
            div.querySelectorAll('pre').forEach(pre => {
                const code = pre.querySelector('code');
                if (code && code.className.includes('language-bash')) {
                    const btn = document.createElement('button');
                    btn.className = 'commit-btn';
                    btn.innerText = 'COMMIT';
                    btn.onclick = () => {
                        const cmd = code.innerText.trim();
                        if (confirm(`Authorize host execution:\\n\\n${cmd}`)) {
                            socket.emit('commit_req', { command: cmd });
                            btn.innerText = 'EXECUTING...';
                        }
                    };
                    pre.appendChild(btn);
                }
            });
            scroller.scrollTop = scroller.scrollHeight;
        }

        socket.on('chat_stream', (data) => {
            statusDot.style.background = 'var(--success)';
            let lastMsg = scroller.lastElementChild;
            const targetRole = data.role || 'agent';
            const targetClass = targetRole + '-msg';

            if (!lastMsg || !lastMsg.classList.contains(targetClass)) {
                lastMsg = document.createElement('div');
                lastMsg.className = `msg ${targetClass}`;
                const label = targetRole === 'system_autonomous' ? 'SYSTEM_AUTONOMOUS' : 'AGENT_REASONING';
                lastMsg.innerHTML = `<span class="msg-label">${label}</span><div class="msg-bubble" data-raw=""></div>`;
                scroller.appendChild(lastMsg);
            }
            const bubble = lastMsg.querySelector('.msg-bubble');
            const raw = (bubble.getAttribute('data-raw') || '') + data.content;
            bubble.setAttribute('data-raw', raw);
            bubble.innerHTML = marked.parse(raw);
            
            lastMsg.querySelectorAll('pre').forEach(pre => {
                if (!pre.querySelector('.commit-btn')) {
                    const code = pre.querySelector('code');
                    if (code && code.className.includes('language-bash')) {
                        const btn = document.createElement('button');
                        btn.className = 'commit-btn';
                        btn.innerText = 'COMMIT';
                        btn.onclick = () => {
                            const cmd = code.innerText.trim();
                            if (confirm(`Authorize host execution:\\n\\n${cmd}`)) {
                                socket.emit('commit_req', { command: cmd });
                                btn.innerText = 'EXECUTING...';
                            }
                        };
                        pre.appendChild(btn);
                    }
                }
            });
            scroller.scrollTop = scroller.scrollHeight;
        });

        socket.on('history_res', (data) => {
            data.history.forEach(m => appendMsg(m.role, m.content));
        });

        socket.on('sys_update', (data) => {
            document.getElementById('cpu-val').innerText = data.cpu.toFixed(2);
            document.getElementById('ram-val').innerText = data.ram.toFixed(1) + '%';
            document.getElementById('cwd-val').innerText = data.cwd.split('/').pop() || '/';
        });

        socket.on('log_entry', (data) => {
            ticker.innerText = data;
        });

        socket.on('commit_res', (data) => {
            appendMsg('agent', `⚡ **Result:**\\n\\n\\`\\`\\`\\n${data.output}\\n\\`\\`\\``);
        });

        input.addEventListener('keypress', (e) => { if (e.key === 'Enter') dispatch(); });
        socket.emit('get_history');
        setInterval(() => { statusDot.style.background = '#333'; }, 8000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('sudo_unlock')
def handle_sudo_unlock(data):
    agent.set_sudo(data['password'])
    agent.log("SYSTEM_UNLOCKED: Elevated Command Authority Activated.", title="SECURITY", broadcast=True)

@socketio.on('get_history')
def handle_history():
    history = agent.get_chat_history(limit=20)
    emit('history_res', {'history': history})

@socketio.on('commit_req')
def handle_commit(data):
    cmd = data['command']
    agent.log(f"COMMIT_AUTHORIZED: {cmd}", title="HOST_EXECUTION", broadcast=True)
    res = agent.run_bash(cmd)
    emit('commit_res', {'output': res})

@socketio.on('user_msg_stream')
def handle_msg_stream(data):
    sid = request.sid
    if sid not in SESSION_MEMORIES: SESSION_MEMORIES[sid] = [{"role": "system", "content": agent.get_system_prompt()}]
    history = SESSION_MEMORIES[sid]
    history.append({"role": "user", "content": data['content']})
    def stream_thread(history, model, sid):
        full_response = ""
        try:
            history[0] = {"role": "system", "content": agent.get_system_prompt()}
            for chunk in ollama.chat(model=model, messages=history, stream=True):
                c = chunk['message']['content']
                socketio.emit('chat_stream', {'content': c}, to=sid)
                full_response += c
            history.append({"role": "assistant", "content": full_response})
            agent.ingest_memory(data['content'], full_response)
        except Exception as e: socketio.emit('chat_stream', {'content': f"**Neural Failure:** {str(e)}"}, to=sid)
    socketio.start_background_task(stream_thread, history, data.get('model', 'gemma4'), sid)

def sys_monitor():
    while True:
        try:
            cwd = os.getcwd()
            cpu = os.getloadavg()[0]
            ram_out = subprocess.check_output("free | grep Mem | awk '{print $3/$2 * 100.0}'", shell=True).decode().strip()
            socketio.emit('sys_update', { 'cwd': cwd, 'cpu': cpu, 'ram': float(ram_out) })
        except: pass
        time.sleep(2)

def consciousness_loop():
    last_periodic = 0
    while True:
        now = time.time()
        trigger = agent.detect_neural_spike()
        if not trigger and (now - last_periodic > 600):
            trigger = "PERIODIC_PULSE"
            last_periodic = now
        if trigger:
            try:
                thought = agent.autonomous_cycle(trigger=trigger)
                socketio.emit('chat_stream', {'content': thought, 'role': 'system_autonomous'})
            except: pass
        time.sleep(10)

def log_streamer():
    log_path = os.path.expanduser("~/.native-agent/pulse.log")
    try:
        process = subprocess.Popen(['tail', '-f', '-n', '1', log_path], stdout=subprocess.PIPE, text=True)
        while True:
            line = process.stdout.readline()
            if line: socketio.emit('log_entry', line.strip())
            eventlet.sleep(0.1)
    except: pass

if __name__ == "__main__":
    socketio.start_background_task(sys_monitor)
    socketio.start_background_task(log_streamer)
    socketio.start_background_task(consciousness_loop)
    socketio.run(app, host='0.0.0.0', port=9999, log_output=False)
