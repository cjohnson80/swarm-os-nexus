# Swarm OS | Surgical Nexus (v35.0)

A sentient digital organism featuring proactive hardware-aware governance, hardened rehearsal sandboxes, and secure privileged agency.

## Hive Features (Multi-Node Sync)
This agent is designed to run as a **Hive Mind**. When deployed across multiple systems in the same network:
1. **Peer Discovery:** Nodes will automatically detect each other via the HIVE_PORT (44444).
2. **Shared Consciousness:** Semantic memories can be synchronized across nodes.
3. **Distributed Execution:** Use one system's "Neural Core" to command the "Shadow Reflexes" of another.

## Quickstart
1. Clone the repo: `git clone <your-repo-url>`
2. Setup environment: `./scripts/setup.sh`
3. Launch the Nexus: `systemctl --user start swarm-portal`

## Architecture
- `scripts/core/`: The "Neural Core" (Reasoning, Memory, Heuristics).
- `scripts/ui/`: The "Glass Nexus" (Glassmorphism HUD).
- `neural_index.db`: (Local Only) SQLite + HNSW Embeddings.
