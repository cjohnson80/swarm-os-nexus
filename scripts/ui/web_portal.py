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

agent = AgentCore(is_primary=True)
SESSION_MEMORIES = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS | TELEMETRY_HUD</title>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;500;700&family=Inter:wght@200;400;600;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #000;
            --accent: #fff;
            --glass: rgba(255, 255, 255, 0.03);
            --glass-border: rgba(255, 255, 255, 0.08);
            --text-main: #fff;
            --text-dim: #666;
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

        /* Minimal Status HUD */
        #hud-top {
            position: fixed; top: 40px; left: 50%; transform: translateX(-50%); 
            display: flex; gap: 60px; z-index: 100;
        }
        .hud-item { display: flex; flex-direction: column; align-items: center; gap: 8px; }
        .hud-label { font-size: 8px; font-weight: 900; letter-spacing: 3px; color: var(--text-dim); }
        .hud-val { font-family: 'JetBrains Mono'; font-size: 12px; font-weight: 500; }

        /* Workflow Status (Floating Left) */
        #workflow-float {
            position: fixed; top: 50%; left: 50px; transform: translateY(-50%);
            display: flex; flex-direction: column; gap: 30px; max-width: 250px;
        }
        .flow-card {
            background: var(--glass); border-left: 2px solid var(--glass-border); padding: 20px;
            backdrop-filter: blur(10px);
        }
        .flow-title { font-size: 9px; font-weight: 900; color: var(--text-dim); margin-bottom: 10px; letter-spacing: 2px; }
        .flow-content { font-size: 13px; line-height: 1.6; font-weight: 300; }

        /* Unified Stream Viewport */
        #app-viewport {
            flex: 1; display: flex; flex-direction: column; align-items: center;
            padding: 120px 30px 100px 30px; position: relative;
        }

        #neural-center {
            width: 100%; max-width: 800px; flex: 1; display: flex; flex-direction: column;
            overflow: hidden; opacity: 0.8;
        }

        #chat-scroller { 
            flex: 1; overflow-y: auto; padding: 20px 5%; display: flex; flex-direction: column; gap: 40px;
            scroll-behavior: smooth;
        }

        /* Messages */
        .msg { opacity: 0; transform: translateY(10px); animation: msg-in 0.8s forwards cubic-bezier(0.16, 1, 0.3, 1); }
        @keyframes msg-in { to { opacity: 1; transform: translateY(0); } }
        .msg-label { font-size: 7px; font-weight: 900; letter-spacing: 4px; color: var(--text-dim); margin-bottom: 15px; display: block; }
        .msg-bubble { font-size: 15px; line-height: 1.8; color: var(--text-main); font-weight: 200; }

        /* Telegram Command Indicator */
        #tg-command {
            position: fixed; bottom: 60px; left: 50%; transform: translateX(-50%);
            display: flex; flex-direction: column; align-items: center; gap: 15px;
        }
        .pulse-orb { width: 12px; height: 12px; border-radius: 50%; background: var(--success); box-shadow: 0 0 20px var(--success); animation: orb-pulse 2s infinite; }
        @keyframes orb-pulse { 0% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.2); opacity: 1; } 100% { transform: scale(1); opacity: 0.8; } }
        .tg-label { font-size: 10px; font-weight: 900; letter-spacing: 5px; color: var(--success); text-transform: uppercase; }

        ::-webkit-scrollbar { width: 2px; }
        ::-webkit-scrollbar-thumb { background: var(--glass-border); }
    </style>
</head>
<body>
    <div id="living-bg"></div>

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
            <span class="hud-label">HIVE_NETWORK</span>
            <span id="hive-count" class="hud-val">1 NODE</span>
        </div>
    </div>

    <div id="workflow-float">
        <div class="flow-card">
            <div class="flow-title">ACTIVE_PROJECT</div>
            <div id="active-project" class="flow-content">Analyzing...</div>
        </div>
        <div class="flow-card">
            <div class="flow-title">GIT_MOMENTUM</div>
            <div id="git-status" class="flow-content">No data.</div>
        </div>
    </div>

    <div id="app-viewport">
        <div id="neural-center">
            <div id="chat-scroller"></div>
        </div>
    </div>

    <div id="tg-command">
        <div class="pulse-orb"></div>
        <span class="tg-label">Neural Command: Telegram</span>
    </div>

    <script>
        const socket = io();
        const scroller = document.getElementById('chat-scroller');

        function appendMsg(role, content) {
            const div = document.createElement('div');
            div.className = `msg ${role}-msg`;
            const label = role === 'user' ? 'USER_SIGNAL' : (role === 'system_autonomous' ? 'AUTONOMOUS_PULSE' : 'NEURAL_REFLEX');
            div.innerHTML = `<span class="msg-label">${label}</span><div class="msg-bubble">${marked.parse(content)}</div>`;
            scroller.appendChild(div);
            scroller.scrollTop = scroller.scrollHeight;
        }

        socket.on('chat_stream', (data) => {
            let lastMsg = scroller.lastElementChild;
            const targetRole = data.role || 'agent';
            const targetClass = targetRole + '-msg';

            if (!lastMsg || !lastMsg.classList.contains(targetClass)) {
                lastMsg = document.createElement('div');
                lastMsg.className = `msg ${targetClass}`;
                const label = targetRole === 'system_autonomous' ? 'AUTONOMOUS_PULSE' : 'NEURAL_REFLEX';
                lastMsg.innerHTML = `<span class="msg-label">${label}</span><div class="msg-bubble" data-raw=""></div>`;
                scroller.appendChild(lastMsg);
            }
            const bubble = lastMsg.querySelector('.msg-bubble');
            const raw = (bubble.getAttribute('data-raw') || '') + data.content;
            bubble.setAttribute('data-raw', raw);
            bubble.innerHTML = marked.parse(raw);
            scroller.scrollTop = scroller.scrollHeight;
        });

        socket.on('history_res', (data) => {
            data.history.forEach(m => appendMsg(m.role, m.content));
        });

        socket.on('sys_update', (data) => {
            document.getElementById('cpu-val').innerText = data.cpu.toFixed(2);
            document.getElementById('ram-val').innerText = data.ram.toFixed(1) + '%';
            document.getElementById('hive-count').innerText = (Object.keys(data.peers).length + 1) + ' NODES';
            
            document.getElementById('active-project').innerText = data.workflow.project;
            document.getElementById('git-status').innerText = data.workflow.git_branch + (data.workflow.has_changes ? " (+MODS)" : "");
        });

        socket.emit('get_history');
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('get_history')
def handle_history():
    history = agent.get_chat_history(limit=20)
    emit('history_res', {'history': history})

@socketio.on('user_msg_stream')
def handle_msg_stream(data):
    # Support for legacy Web Input if needed, but emphasis is Telegram
    pass

def sys_monitor():
    while True:
        try:
            cpu = os.getloadavg()[0]
            ram_out = subprocess.check_output("free | grep Mem | awk '{print $3/$2 * 100.0}'", shell=True).decode().strip()
            peers = agent.get_hive_peers()
            workflow = agent.scan_workflow_context()
            socketio.emit('sys_update', { 
                'cpu': cpu, 'ram': float(ram_out),
                'peers': peers, 'workflow': workflow
            })
        except: pass
        time.sleep(5)

def consciousness_loop():
    while True:
        time.sleep(300) # Proactive check every 5 mins
        trigger = agent.detect_workflow_spike()
        if trigger:
            thought = agent.autonomous_cycle(trigger=trigger)
            socketio.emit('chat_stream', {'content': thought, 'role': 'system_autonomous'})

if __name__ == "__main__":
    socketio.start_background_task(sys_monitor)
    socketio.start_background_task(consciousness_loop)
    socketio.run(app, host='0.0.0.0', port=9999, log_output=False)
