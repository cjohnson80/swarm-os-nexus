#!/home/chrisj/.native-agent/venv/bin/python3
import ollama
import subprocess
import os
import time
import re
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.theme import Theme
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
import select
import termios
import tty
import concurrent.futures

from agent_core import AgentCore, AGENT_WING, SKILLS_DIR

custom_theme = Theme({
    "info": "dim cyan",
    "danger": "bold red",
    "exec": "bold yellow",
    "result": "green",
    "user": "bold blue",
    "agent": "bold cyan",
    "palace": "bold magenta",
    "plan": "bold yellow",
    "web": "bold green",
    "delegate": "bold blue",
    "vision": "bold white on purple",
    "notify": "bold white on red"
})

console = Console(theme=custom_theme)
agent = AgentCore(console=console)

def show_help():
    t = Table(title="Neural Swarm OS v16.1 (Neural Nexus)", border_style="cyan")
    t.add_column("Command"); t.add_column("Description")
    t.add_row("/help", "Show this help")
    t.add_row("/yolo", "Toggle God-Mode (YOLO)")
    t.add_row("/guardian", "Trigger Holographic Guardian scan")
    t.add_row("/compress_mem", "Distill MemPalace into Knowledge Core")
    t.add_row("/cd <path>", "Spatial Movement")
    t.add_row("/forge <file>", "Integrated Code Editing")
    t.add_row("/oracle", "Regenerate Morning Briefing")
    t.add_row("/vibe", "System Sentiment Analysis")
    t.add_row("/speak <text>", "Biological output")
    t.add_row("/exit", "Shutdown")
    console.print(t)

def create_dashboard(model_name):
    yolo = "[bold red]YOLO[/bold red]" if agent.yolo_mode else "[green]SAFE[/green]"
    try:
        mem = subprocess.run("free -h | grep Mem | awk '{print $3 \"/\" $2}'", shell=True, capture_output=True, text=True).stdout.strip()
        load = subprocess.run("uptime | awk -F'load average:' '{ print $2 }' | cut -d',' -f1", shell=True, capture_output=True, text=True).stdout.strip()
    except: mem = "N/A"; load = "N/A"
    
    vibe = agent.get_vibe()
    peers = [p for p in agent.peers.values() if time.time() - p['last_seen'] < 600]
    cwd = os.getcwd()
    status = f"[agent]OS GHOST[/agent] | {vibe} | {yolo} | [info]MEM:[/info] {mem} | [info]LOAD:[/info] {load} | [agent]HIVE:[/agent] {len(peers)} | [cyan]CWD:[/cyan] {cwd}"
    return Panel(status, border_style="cyan", padding=(0, 1))

def check_interrupt():
    if not sys.stdin.isatty(): return False
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        r, _, _ = select.select([sys.stdin], [], [], 0)
        if r:
            char = sys.stdin.read(1)
            if char == '\x1b': return True
    finally: termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return False

def chat():
    subprocess.run("clear", shell=True)
    current_model = "gemma4"
    agent.start_hive_discovery()
    agent.hive_heartbeat()
    agent.speak("Omega Initiative initialized. Opening data port.")
    
    console.print(create_dashboard(current_model))
    
    # Proactive Spatial Discovery
    with console.status("[cyan]Initiating Proactive Spatial Discovery...[/cyan]"):
        discovery_res = agent.run_discovery("~/Projects")
    
    # Morning Briefing
    with console.status("[magenta]Synthesizing Hive Intelligence Report...[/magenta]"):
        briefing = agent.generate_morning_briefing()
    
    console.print(Panel(briefing, title="[magenta]Oracle: Morning Briefing[/magenta]", border_style="magenta"))
    agent.speak("Good morning. Here is your Hive Intelligence report.")

    messages = [
        {"role": "system", "content": agent.get_system_prompt()},
        {"role": "user", "content": f"INITIAL DISCOVERY REPORT:\n{discovery_res}\n\nMORNING BRIEFING:\n{briefing}\n\nAgent, the data port is open. Analyze the blueprints and briefing above and report your decisive strategy."}
    ]
    
    while True:
        try:
            console.print(create_dashboard(current_model))
            user_input = Prompt.ask("\n[user]User[/user]")
        except (EOFError, KeyboardInterrupt): break
        if not user_input: continue
        
        if user_input.startswith("/"):
            parts = user_input.split(); cmd = parts[0].lower()
            if cmd == "/exit": break
            if cmd == "/yolo": agent.yolo_mode = not agent.yolo_mode; continue
            if cmd == "/guardian": console.print(Panel(agent.run_guardian(), title="Security Scan", border_style="red")); continue
            if cmd == "/compress_mem": console.print(Panel(agent.run_compress_mem(), title="Memory Distillation", border_style="magenta")); continue
            if cmd == "/cd" and len(parts) > 1:
                try: os.chdir(os.path.expanduser(parts[1])); console.print(f"[green]Moved to {os.getcwd()}[/green]")
                except Exception as e: console.print(f"[danger]CD Error: {e}[/danger]")
                continue
            if cmd == "/help": show_help(); continue
            continue

        messages.append({"role": "user", "content": user_input})
        
        while True:
            messages[0]["content"] = agent.get_system_prompt()
            content = ""
            console.print(f"\n[agent]Agent[/agent] [dim](Esc to interrupt)[/dim]")
            interrupted = False
            try:
                with Live(Spinner("dots", text="[dim]Ghosting...[/dim]"), refresh_per_second=10, console=console) as live:
                    for chunk in ollama.chat(model=current_model, messages=messages, stream=True):
                        content += chunk['message']['content']
                        if content: live.update(Markdown(content))
                        if check_interrupt(): interrupted = True; break
            except Exception as e: console.print(f"[danger]Error: {e}[/danger]"); break
            
            if interrupted: content += " [INTERRUPTED]"; console.print("\n[danger]Halt received.[/danger]")
            messages.append({"role": "assistant", "content": content})

            try:
                gui_m = re.search(r"```gui\n(.*?)\n```", content, re.DOTALL)
                browse_m = re.search(r"```browse\n(.*?)\n(.*?)\n```", content, re.DOTALL)
                guardian_m = re.search(r"```guardian\n```", content, re.DOTALL)
                compress_m = re.search(r"```compress_mem\n```", content, re.DOTALL)
                synthesis_c_m = re.search(r"```synthesis_c\n(.*?)\n(.*?)\n(.*?)\n```", content, re.DOTALL)
                twin_m = re.search(r"```twin\n(.*?)\n```", content, re.DOTALL)
                bash_m = re.search(r"```bash\n(.*?)\n```", content, re.DOTALL)
                rewrite_m = re.search(r"```rewrite\n(.*?)\n(.*?)\n```", content, re.DOTALL)
                query_fs_m = re.search(r"```query_fs\n(.*?)\n```", content, re.DOTALL)
                migrate_m = re.search(r"```migrate\n(.*?)\n(.*?)\n```", content, re.DOTALL)
                
                res = None
                if migrate_m: res = agent.run_migrate(migrate_m.group(1), migrate_m.group(2))
                elif gui_m: res = agent.run_gui(gui_m.group(1))
                elif browse_m: res = agent.run_browse(browse_m.group(1), browse_m.group(2))
                elif guardian_m: res = agent.run_guardian()
                elif compress_m: res = agent.run_compress_mem()
                elif synthesis_c_m: res = agent.run_synthesis_c(synthesis_c_m.group(1), synthesis_c_m.group(2), synthesis_c_m.group(3))
                elif twin_m: res = agent.run_twin(twin_m.group(1))
                elif bash_m: 
                    res = agent.run_bash(bash_m.group(1))
                    agent.update_predictive_model(bash_m.group(1))
                elif rewrite_m: res = agent.run_rewrite(rewrite_m.group(1), rewrite_m.group(2))
                elif query_fs_m: res = agent.run_query_fs(query_fs_m.group(1))
                
                if res:
                    console.print(Panel(res, title="Execution Result", border_style="green"))
                    messages.append({"role": "user", "content": f"Result:\n{res}"})
                    continue
                else: break
            except Exception as e:
                console.print(f"[danger]Core Error: {e}[/danger]"); break

if __name__ == "__main__":
    import sys
    try: chat()
    except KeyboardInterrupt: console.print("\n[warning]Offline.[/warning]")
    except Exception as e: console.print(f"\n[danger]Fatal: {e}[/danger]")
    finally: sys.exit(0)
