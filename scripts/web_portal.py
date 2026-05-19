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
    <title>Swarm OS | peak-nexus v30.1</title>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/ace/1.32.2/ace.min.js"></script>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" />
    <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
    <style>
        :root { 
            --bg: #000; --panel: #0a0a0a; --accent: #fff; --subtle: #1a1a1a;
            --text-main: #eee; --text-dim: #888; --border: #222;
            --success: #00ff41; --danger: #ff3131;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; outline: none; }
        body { 
            background: var(--bg); color: var(--text-main); font-family: 'Inter', sans-serif; 
            height: 100vh; overflow: hidden; display: flex;
        }

        #sidebar-left, #sidebar-right { 
            width: 300px; background: var(--bg); border-right: 1px solid var(--border); 
            display: flex; flex-direction: column;
        }
        #sidebar-right { border-left: 1px solid var(--border); border-right: none; width: 340px; }

        .section-header { 
            padding: 24px 20px 12px; font-size: 11px; font-weight: 900; letter-spacing: 2px; 
            color: var(--text-dim); text-transform: uppercase;
        }

        #main-nexus { flex: 1; display: flex; flex-direction: column; background: var(--bg); }

        .tab-bar { display: flex; padding: 0 24px; gap: 30px; border-bottom: 1px solid var(--border); }
        .tab { 
            padding: 24px 0; font-size: 12px; font-weight: 700; color: var(--text-dim); 
            cursor: pointer; position: relative; letter-spacing: 1px; text-transform: uppercase;
        }
        .tab.active { color: var(--accent); }
        .tab.active::after { 
            content: ''; position: absolute; bottom: 0; left: 0; width: 100%; height: 2px; 
            background: var(--accent);
        }

        .bento-card { 
            background: var(--panel); border: 1px solid var(--border); border-radius: 6px; 
            margin: 0 20px 20px; padding: 24px;
        }

        .gauge-wrap { margin-bottom: 20px; }
        .gauge-top { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .gauge-label { font-size: 10px; font-weight: 800; color: var(--text-dim); letter-spacing: 1px; }
        .gauge-val { font-size: 11px; font-family: 'JetBrains Mono'; font-weight: 700; color: var(--text-main); }
        .gauge-bar-bg { height: 3px; background: #111; position: relative; border-radius: 2px;}
        .gauge-bar-fill { height: 100%; background: var(--accent); width: 0%; border-radius: 2px; transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1); }

        #chat-scroller { flex: 1; overflow-y: auto; padding: 40px; display: flex; flex-direction: column; gap: 32px; }
        .msg { margin-bottom: 32px; }
        .msg-label { font-size: 10px; font-weight: 900; letter-spacing: 2px; margin-bottom: 12px; display: block; }
        .user-msg .msg-label { color: var(--accent); }
        .agent-msg .msg-label { color: var(--text-dim); }
        
        .msg-bubble { 
            font-size: 15px; line-height: 1.8; color: var(--text-main); 
            background: rgba(255,255,255,0.02); padding: 24px; border-radius: 4px;
            border: 1px solid var(--border);
        }
        .user-msg .msg-bubble { border-left: 4px solid var(--accent); }
        .agent-msg .msg-bubble { border-left: 4px solid var(--text-dim); }

        .thought-block { 
            border-left: 2px solid #333; padding: 16px 24px; color: #666; 
            font-size: 14px; font-style: italic; margin-bottom: 24px; background: #050505;
        }

        .input-wrapper { display: flex; align-items: center; border: 1px solid var(--border); padding: 6px 20px; border-radius: 4px; background: var(--panel); margin: 20px 40px;}
        .main-input { flex: 1; background: transparent; border: none; color: white; font-family: inherit; font-size: 15px; padding: 14px 0; }
        .btn-send { background: var(--accent); color: var(--bg); border: none; padding: 12px 24px; font-size: 11px; font-weight: 900; letter-spacing: 1px; cursor: pointer; }

        .explorer-item { 
            padding: 14px 20px; font-family: 'JetBrains Mono'; font-size: 12px; color: var(--text-dim);
            cursor: pointer; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #111;
        }
        .explorer-item:hover { color: var(--accent); background: #080808; }

        #terminal-container { height: 280px; background: #000; border-top: 1px solid var(--border); padding: 16px; }
        
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-thumb { background: #333; }
    </style>
</head>
<body>
    <div id="sidebar-left">
        <div class="section-header">Sensory Hub</div>
        <div class="bento-card">
            <div class="gauge-wrap">
                <div class="gauge-top"><span class="gauge-label">CPU_RSN</span><span id="cpu-val" class="gauge-val">0%</span></div>
                <div class="gauge-bar-bg"><div id="cpu-fill" class="gauge-bar-fill"></div></div>
            </div>
            <div class="gauge-wrap">
                <div class="gauge-top"><span class="gauge-label">MEM_SYNC</span><span id="ram-val" class="gauge-val">0%</span></div>
                <div class="gauge-bar-bg"><div id="ram-fill" class="gauge-bar-fill"></div></div>
            </div>
            <div class="gauge-wrap">
                <div class="gauge-top"><span class="gauge-label">DISK_IO</span><span id="disk-val" class="gauge-val">0%</span></div>
                <div class="gauge-bar-bg"><div id="disk-fill" class="gauge-bar-fill"></div></div>
            </div>
        </div>
        
        <div class="section-header">Spatial Hub</div>
        <div style="padding: 0 20px 20px;">
            <input type="text" id="path-jump" placeholder="Jump to path..." 
                   style="background:var(--panel); border:1px solid var(--border); color:white; font-size:12px; width:100%; padding:14px; border-radius:4px;"
                   onkeypress="if(event.key==='Enter') socket.emit('sys_cmd', {command: '/cd ' + this.value})">
            <div id="path-id" style="font-size:10px; color:var(--text-dim); margin-top:12px; font-family:'JetBrains Mono';"></div>
        </div>
        <div id="files-grid" class="explorer-grid" style="flex:1; overflow-y:auto;"></div>
    </div>

    <div id="main-nexus">
        <div class="tab-bar">
            <div id="tab-chat" class="tab active" onclick="showPane('chat')">Neural</div>
            <div id="tab-oracle" class="tab" onclick="showPane('oracle'); fetchBriefing();">Oracle</div>
            <div id="tab-twin" class="tab" onclick="showPane('twin')">Twin</div>
            <div id="tab-fabric" class="tab" onclick="showPane('fabric'); fetchBlackboard();">Fabric</div>
            <div id="tab-vision" class="tab" onclick="showPane('vision')">Vision</div>
            <div id="tab-temporal" class="tab" onclick="showPane('temporal'); fetchGitLog();">Temporal</div>
            <div id="tab-forge" class="tab" onclick="showPane('forge')">Forge</div>
        </div>

        <div id="chat-pane" style="display:flex; flex-direction:column; flex:1;">
            <div id="search-bar" style="padding: 20px 40px 0; display:flex; gap:10px;">
                <input type="text" placeholder="Neural Search..." 
                       style="background:var(--panel); border:1px solid var(--border); color:var(--text-main); font-size:13px; width:100%; padding:14px; border-radius:4px; flex:1;"
                       onkeypress="if(event.key==='Enter') socket.emit('search_req', {query: this.value})">
                <select id="chat-model-select" style="background:var(--panel); border:1px solid var(--border); color:var(--text-main); font-size:11px; padding:0 10px; border-radius:4px;"></select>
                <div style="display:flex; align-items:center; gap:8px; border:1px solid var(--border); padding:0 15px; border-radius:4px;">
                    <input type="checkbox" id="sandbox-toggle"> <label style="font-size:9px;">SANDBOX</label>
                </div>
            </div>
            <div id="chat-scroller"></div>
            <div class="input-wrapper">
                <input type="text" id="cmd-input" class="main-input" placeholder="Execute command..." autocomplete="off">
                <button onclick="dispatch()" class="btn-send">TRANSMIT</button>
            </div>
            <div id="terminal-container"></div>
        </div>

        <div id="oracle-pane" style="display:none; padding:40px; overflow-y:auto; flex:1;">
            <div class="bento-card" style="margin:0; border:1px solid var(--accent);">
                <div class="section-header" style="padding:0; margin-bottom:20px; color:var(--accent);">Strategic Directive [v30.1]</div>
                <div id="strategic-wisdom" style="font-size:16px; line-height:2; color:var(--text-main); font-weight:500;">Initializing consciousness stream...</div>
            </div>
            <div id="briefing-content" style="max-width: 800px; margin: 40px auto; line-height: 2;"></div>
        </div>

        <div id="twin-pane" style="display:none; padding:40px; flex:1; flex-direction:column;">
            <div class="bento-card" style="margin:0; flex:1; display:flex; flex-direction:column;">
                <div class="section-header" style="padding:0; margin-bottom:24px;">Digital Twin (Simulation)</div>
                <input type="text" id="sim-input" placeholder="Enter simulation command..." style="background:var(--bg); border:1px solid var(--border); color:white; font-size:14px; padding:16px; border-radius:4px; margin-bottom:20px;">
                <button onclick="socket.emit('sim_req', {command: document.getElementById('sim-input').value})" class="btn-send">RUN SIMULATION</button>
                <div id="sim-output" style="flex:1; background:#000; padding:20px; font-family:'JetBrains Mono'; font-size:12px; margin-top:20px; border:1px solid var(--border); overflow-y:auto; white-space:pre;"></div>
            </div>
        </div>

        <div id="fabric-pane" style="display:none; padding:40px; flex:1; flex-direction:column;">
            <div class="bento-card" style="margin:0; flex:1;">
                <div class="section-header" style="padding:0; margin-bottom:24px;">Swarm Fabric</div>
                <div style="display:grid; grid-template-columns: 1fr 2fr auto; gap:10px;">
                    <select id="worker-role" style="background:var(--bg); border:1px solid var(--border); color:white; padding:12px;"></select>
                    <input type="text" id="worker-task" placeholder="Task description..." style="background:var(--bg); border:1px solid var(--border); color:white; padding:12px;">
                    <button onclick="socket.emit('spawn_req', {name: 'Worker', task: document.getElementById('worker-task').value, role: document.getElementById('worker-role').value})" class="btn-send">SPAWN</button>
                </div>
                <div id="blackboard-data" style="margin-top:20px; font-family:'JetBrains Mono'; color:var(--text-dim); font-size:12px; white-space:pre;"></div>
            </div>
        </div>

        <div id="vision-pane" style="display:none; padding:40px; flex:1;">
            <div class="bento-card" style="margin:0; flex:1;">
                <div class="section-header" style="padding:0; margin-bottom:24px;">Vision</div>
                <div style="display:flex; gap:10px;">
                    <input type="text" id="vision-prompt" placeholder="Analyze what?" style="background:var(--bg); border:1px solid var(--border); color:white; flex:1; padding:12px;">
                    <select id="vision-model-select" style="background:var(--bg); border:1px solid var(--border); color:white;"></select>
                    <button onclick="socket.emit('vision_req', {prompt: document.getElementById('vision-prompt').value, model: document.getElementById('vision-model-select').value})" class="btn-send">ANALYZE</button>
                </div>
                <div id="vision-result" style="margin-top:20px; font-size:14px; line-height:1.6; color:var(--text-dim);"></div>
            </div>
        </div>

        <div id="temporal-pane" style="display:none; padding:40px; flex:1;">
            <div id="git-log-container" style="background:#000; padding:24px; font-family:'JetBrains Mono'; font-size:12px; color:var(--text-dim); white-space:pre; border:1px solid var(--border); height:100%; overflow-y:auto;"></div>
        </div>

        <div id="forge-pane" style="display:none; flex:1; flex-direction:column;">
            <div class="forge-header" style="padding:20px; border-bottom:1px solid var(--border);">
                <span id="active-file">No file selected.</span>
                <button onclick="saveForge()" class="btn-send" style="padding:8px 16px;">SAVE</button>
            </div>
            <div id="editor" style="flex:1;"></div>
        </div>
    </div>

    <div id="sidebar-right">
        <div class="section-header">Consciousness Control</div>
        <div class="bento-card" style="margin:0 20px 20px; padding:16px;">
            <button onclick="socket.emit('wisdom_req')" style="width:100%; background:transparent; border:1px solid var(--border); color:var(--text-main); padding:12px; font-size:10px; font-weight:800; cursor:pointer; margin-bottom:12px;">GENERATE DIRECTIVE</button>
            <button onclick="socket.emit('gardener_v4_req')" style="width:100%; background:transparent; border:1px solid var(--border); color:var(--text-main); padding:12px; font-size:10px; font-weight:800; cursor:pointer;">RUN GARDENER v4</button>
        </div>
        <div class="section-header">Active Objectives</div>
        <div id="missions-grid" class="explorer-grid"></div>
        <div class="section-header">Swarm Intel</div>
        <div id="intel-grid" class="explorer-grid" style="flex:1; overflow-y:auto;"></div>
    </div>

    <script>
        const socket = io();
        const input = document.getElementById('cmd-input');
        const scroller = document.getElementById('chat-scroller');
        
        const term = new Terminal({
            theme: { background: '#000', foreground: '#eee', cursor: '#fff' },
            fontSize: 12, fontFamily: 'JetBrains Mono', rows: 12
        });
        term.open(document.getElementById('terminal-container'));

        const editor = ace.edit("editor");
        editor.setTheme("ace/theme/tomorrow_night_eighties");
        editor.session.setMode("ace/mode/python");

        function dispatch(override) {
            const val = override || input.value.trim();
            if (!val) return;
            const isSandboxed = document.getElementById('sandbox-toggle').checked;
            if (val.startsWith('/')) {
                socket.emit('sys_cmd', { command: val, sandbox: isSandboxed });
            } else {
                const wrap = document.createElement('div');
                wrap.className = 'msg user-msg';
                wrap.innerHTML = `<span class="msg-label">USER_INPUT</span><div class="msg-bubble">${val}</div>`;
                scroller.appendChild(wrap);
                socket.emit('user_msg_stream', { content: val, model: document.getElementById('chat-model-select').value, sandbox: isSandboxed });
            }
            if (!override) input.value = '';
            scroller.scrollTop = scroller.scrollHeight;
        }

        socket.on('chat_stream', (data) => {
            let lastMsg = scroller.lastElementChild;
            if (!lastMsg || !lastMsg.classList.contains('agent-msg')) {
                lastMsg = document.createElement('div');
                lastMsg.className = 'msg agent-msg';
                lastMsg.innerHTML = `<span class="msg-label">AGENT_REASONING</span><div class="msg-bubble"></div>`;
                scroller.appendChild(lastMsg);
            }
            const bubble = lastMsg.querySelector('.msg-bubble');
            if (data.is_thought) {
                let thought = lastMsg.querySelector('.thought-block');
                if (!thought) {
                    thought = document.createElement('div');
                    thought.className = 'thought-block';
                    lastMsg.insertBefore(thought, bubble);
                }
                thought.innerText += data.content;
            } else {
                bubble.innerHTML = marked.parse(bubble.innerText + data.content);
            }
            scroller.scrollTop = scroller.scrollHeight;
        });

        socket.on('sys_update', (data) => {
            document.getElementById('cpu-val').innerText = data.cpu.toFixed(1) + '%';
            document.getElementById('cpu-fill').style.width = Math.min(data.cpu, 100) + '%';
            document.getElementById('ram-val').innerText = data.ram.toFixed(1) + '%';
            document.getElementById('ram-fill').style.width = data.ram + '%';
            document.getElementById('disk-val').innerText = data.disk.toFixed(1) + '%';
            document.getElementById('disk-fill').style.width = data.disk + '%';
            document.getElementById('path-id').innerText = data.cwd;

            document.getElementById('files-grid').innerHTML = data.files.map(f => `
                <div class="explorer-item" onclick="selectFile('${f.name}', ${f.is_dir})">
                    <span>${f.is_dir ? '[DIR]' : '[FILE]'} ${f.name}</span>
                </div>
            `).join('');

            document.getElementById('missions-grid').innerHTML = data.missions.map(m => `
                <div class="explorer-item"><span>[${m.status.toUpperCase()}] ${m.text}</span></div>
            `).join('');

            document.getElementById('intel-grid').innerHTML = data.logs.map(l => `
                <div class="explorer-item" style="flex-direction:column; align-items:flex-start;">
                    <span style="color:#10b981; font-size:10px;">${l.substring(0,60)}...</span>
                    <button onclick="socket.emit('intel_analyze_req', {content: '${l.replace(/'/g, "\\\\'")}'})" style="color:var(--accent); font-size:8px; margin-top:4px;">ANALYZE</button>
                </div>
            `).join('');
        });

        socket.on('wisdom_res', (data) => { document.getElementById('strategic-wisdom').innerText = data.directive; });
        socket.on('models_res', (data) => {
            const chatSel = document.getElementById('chat-model-select');
            const visSel = document.getElementById('vision-model-select');
            chatSel.innerHTML = data.models.map(m => `<option value="${m}" ${m.includes('deepseek') ? 'selected' : ''}>${m}</option>`).join('');
            visSel.innerHTML = data.models.map(m => `<option value="${m}" ${m.includes('moondream') ? 'selected' : ''}>${m}</option>`).join('');
        });
        socket.on('templates_res', (data) => { document.getElementById('worker-role').innerHTML = data.templates.map(t => `<option value="${t}">${t}</option>`).join(''); });
        socket.on('blackboard_res', (data) => { document.getElementById('blackboard-data').innerText = data.data; });
        socket.on('vision_res', (data) => { document.getElementById('vision-result').innerText = data.result; });
        socket.on('git_log_res', (data) => { document.getElementById('git-log-container').innerText = data.log; });
        socket.on('sim_res', (data) => { document.getElementById('sim-output').innerText = data.output; });
        
        socket.on('agent_response', (data) => {
            editor.setValue(data.forge_content, -1);
            document.getElementById('active-file').innerText = data.filename;
            showPane('forge');
        });

        function showPane(pane) {
            ['chat', 'oracle', 'twin', 'fabric', 'vision', 'temporal', 'forge'].forEach(p => {
                const el = document.getElementById(p + '-pane');
                if (el) el.style.display = p === pane ? 'flex' : 'none';
                const tab = document.getElementById('tab-' + p);
                if (tab) tab.classList.toggle('active', p === pane);
            });
        }

        function selectFile(name, isDir) {
            if (isDir) socket.emit('sys_cmd', {command: '/cd ' + name});
            else {
                document.getElementById('active-file').innerText = name;
                socket.emit('sys_cmd', {command: '/forge ' + name});
            }
        }

        function saveForge() {
            socket.emit('save_forge', { filename: document.getElementById('active-file').innerText, content: editor.getValue() });
        }

        function fetchBriefing() { socket.emit('wisdom_req'); }
        function fetchBlackboard() { socket.emit('blackboard_req'); socket.emit('get_templates_req'); }

        input.addEventListener('keypress', (e) => { if (e.key === 'Enter') dispatch(); });
        socket.emit('get_models_req');
        fetchBriefing();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('sys_cmd')
def handle_sys_cmd(data):
    cmd_parts = data['command'].split(' ', 1)
    is_sandboxed = data.get('sandbox', False)
    if cmd_parts[0] == "/cd":
        try:
            os.chdir(os.path.abspath(os.path.join(os.getcwd(), cmd_parts[1] if len(cmd_parts)>1 else "")))
            emit('chat_stream', {'content': f"**Spatial Hub:** Moved to `{os.getcwd()}`", 'is_thought': False})
        except Exception as e:
            emit('chat_stream', {'content': f"**Error:** {str(e)}", 'is_thought': False})
    elif cmd_parts[0] == "/forge":
        try:
            with open(cmd_parts[1], 'r') as f: c = f.read()
            emit('agent_response', {'forge_content': c, 'filename': os.path.abspath(cmd_parts[1])})
        except Exception as e:
            emit('chat_stream', {'content': f"**Forge Error:** {str(e)}", 'is_thought': False})
    else:
        res = agent.run_sandboxed(data['command']) if is_sandboxed else agent.run_bash(data['command'])
        emit('execution_result', {'command': data['command'], 'result': res})

@socketio.on('user_msg_stream')
def handle_msg_stream(data):
    sid = request.sid
    if sid not in SESSION_MEMORIES: SESSION_MEMORIES[sid] = [{"role": "system", "content": agent.get_system_prompt()}]
    history = SESSION_MEMORIES[sid]
    history.append({"role": "user", "content": data['content']})

    def stream_thread(history, model, sid, sandboxed):
        full_response = ""
        full_thought = ""
        in_thought = False
        try:
            for chunk in ollama.chat(model=model, messages=history, stream=True):
                c = chunk['message']['content']
                if "<think>" in c: in_thought = True; c = c.replace("<think>", "")
                if "</think>" in c: in_thought = False; c = c.replace("</think>", "")
                socketio.emit('chat_stream', {'content': c, 'is_thought': in_thought}, to=sid)
                if not in_thought: full_response += c
                else: full_thought += c
            history.append({"role": "assistant", "content": full_thought + "\\n" + full_response})
            bash_m = re.search(r"```bash\\n(.*?)\\n```", full_response, re.DOTALL)
            if bash_m:
                cmd = bash_m.group(1).strip()
                res = agent.run_sandboxed(cmd) if sandboxed else agent.run_bash(cmd)
                socketio.emit('execution_result', {'command': cmd, 'result': res}, to=sid)
        except Exception as e: socketio.emit('chat_stream', {'content': f"**Neural Failure:** {str(e)}", 'is_thought': False}, to=sid)
    socketio.start_background_task(stream_thread, history, data.get('model', 'deepseek-r1:1.5b'), sid, data.get('sandbox', False))

@socketio.on('get_models_req')
def handle_get_models(): emit('models_res', {'models': agent.get_available_models()})
@socketio.on('get_templates_req')
def handle_templates(): emit('templates_res', {'templates': list(agent.get_agent_templates().keys())})
@socketio.on('spawn_req')
def handle_spawn(data): emit('chat_stream', {'content': f"**Swarm Fabric:** {agent.spawn_worker(data['name'], data['task'], role=data.get('role'))}", 'is_thought': False})
@socketio.on('blackboard_req')
def handle_blackboard(): emit('blackboard_res', {'data': agent.blackboard_get()})
@socketio.on('vision_req')
def handle_vision(data): emit('vision_res', {'result': agent.analyze_vision(data.get('prompt'), model=data.get('model'))})
@socketio.on('search_req')
def handle_search(data): emit('chat_stream', {'content': f"### [Semantic Search]\\n\\n{agent.semantic_search(data['query'])}", 'is_thought': False})
@socketio.on('git_log_req')
def handle_git_log(): 
    try: emit('git_log_res', {'log': subprocess.check_output("git log --oneline -n 50", shell=True).decode()})
    except: emit('git_log_res', {'log': 'No Git detected.'})
@socketio.on('sim_req')
def handle_sim(data): emit('sim_res', agent.run_digital_twin(data['command']))
@socketio.on('save_forge')
def handle_save(data): 
    with open(data['filename'], 'w') as f: f.write(data['content'])
    emit('chat_stream', {'content': f"**Forge:** Saved `{data['filename']}`", 'is_thought': False})
@socketio.on('wisdom_req')
def handle_wisdom(): emit('wisdom_res', {'directive': agent.generate_strategic_directive()})
@socketio.on('gardener_v4_req')
def handle_gardener_v4(): emit('chat_stream', {'content': f"**Gardener v4:** {agent.execute_gardener_v4()}", 'is_thought': False})
@socketio.on('intel_analyze_req')
def handle_intel_analyze(data):
    for chunk in ollama.chat(model='deepseek-r1:1.5b', messages=[{"role": "user", "content": f"Analyze this log: {data['content']}"}], stream=True):
        socketio.emit('chat_stream', {'content': chunk['message']['content'], 'is_thought': False}, to=request.sid)

def sys_monitor():
    while True:
        try:
            cwd = os.getcwd()
            cpu = os.getloadavg()[0] * 10
            ram_out = subprocess.check_output("free | grep Mem | awk '{print $3/$2 * 100.0}'", shell=True).decode().strip()
            disk_out = subprocess.check_output("df / | tail -1 | awk '{print $5}' | sed 's/%//'", shell=True).decode().strip()
            files = [{"name": f, "is_dir": os.path.isdir(os.path.join(cwd, f))} for f in sorted(os.listdir(cwd))[:40]]
            socketio.emit('sys_update', {
                'cwd': cwd, 'cpu': cpu, 'ram': float(ram_out), 'disk': float(disk_out), 'files': files,
                'missions': agent.get_missions()[:10], 'logs': agent.get_swarm_logs(limit=8)
            })
            agent.perform_sentinel_prime()
        except: pass
        time.sleep(4)

if __name__ == "__main__":
    socketio.start_background_task(sys_monitor)
    socketio.run(app, host='0.0.0.0', port=9999, log_output=False)
