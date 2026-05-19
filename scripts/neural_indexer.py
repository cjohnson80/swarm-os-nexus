import os
import json
import ollama
import time
import sqlite3
import numpy as np

# Neural Indexer v1.0
# Uses nomic-embed-text to build a persistent semantic memory

DB_PATH = os.path.expanduser("~/.native-agent/neural_index.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS embeddings 
                  (path TEXT PRIMARY KEY, content TEXT, vector BLOB, last_mod REAL)''')
    conn.commit()
    return conn

def get_embedding(text):
    res = ollama.embeddings(model="nomic-embed-text", prompt=text)
    return res['embedding']

def index_project(root_dir):
    conn = init_db()
    cur = conn.cursor()
    
    print(f"Neural Indexer: Scanning {root_dir}")
    for root, dirs, files in os.walk(root_dir):
        if ".git" in root or "__pycache__" in root or "venv" in root: continue
        
        for file in files:
            if not file.endswith(('.py', '.js', '.md', '.json', '.txt')): continue
            
            path = os.path.join(root, file)
            mtime = os.path.getmtime(path)
            
            # Check if updated
            cur.execute("SELECT last_mod FROM embeddings WHERE path=?", (path,))
            row = cur.fetchone()
            if row and row[0] >= mtime: continue
            
            print(f"Indexing: {file}")
            try:
                with open(path, 'r') as f:
                    content = f.read()
                if len(content) < 10: continue
                
                # We embed the first 2k chars for now
                vector = get_embedding(content[:2000])
                cur.execute("INSERT OR REPLACE INTO embeddings VALUES (?, ?, ?, ?)",
                            (path, content[:1000], json.dumps(vector), mtime))
                conn.commit()
            except: continue

    conn.close()
    print("Neural Indexer: Cycle Complete.")

if __name__ == "__main__":
    # Start indexing from the native-agent base
    index_project(os.path.expanduser("~/.native-agent"))
