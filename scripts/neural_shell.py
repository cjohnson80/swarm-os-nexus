#!/home/chrisj/.native-agent/venv/bin/python3
import sys
import ollama
import json
import os
from rich.console import Console

console = Console()
PREDICT_FILE = os.path.expanduser("~/.native-agent/predictions.json")

def suggest_fix(failed_command):
    history = []
    if os.path.exists(PREDICT_FILE):
        try:
            with open(PREDICT_FILE, 'r') as f: history = json.load(f)
        except: pass

    prompt = f"""User just typed a command that failed: `{failed_command}`
RECENT SUCCESSFUL COMMANDS: {history[-5:]}

1. Provide a corrected version of the failed command.
2. PREDICT the MOST LIKELY NEXT command they will want to run after the fix.

Format:
FIX: <command>
PREDICTION: <command>

No explanation. raw commands only.
"""
    try:
        response = ollama.chat(model="gemma4", messages=[{"role": "user", "content": prompt}])
        content = response['message']['content']
        
        fix = re.search(r"FIX: (.*?)\n", content)
        pred = re.search(r"PREDICTION: (.*)", content)
        
        if fix:
            console.print(f"\n[bold yellow]🧠 Neural Fix:[/bold yellow] [bold green]{fix.group(1).strip()}[/bold green]")
        if pred:
            console.print(f"[bold cyan]🔮 Pre-Cog Prediction:[/bold cyan] [dim]{pred.group(1).strip()}[/dim]")
        
        console.print("[dim]Copy/paste to run.[/dim]\n")
    except: pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        suggest_fix(" ".join(sys.argv[1:]))
