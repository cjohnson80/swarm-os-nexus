#!/bin/bash

# NEXUS_SETUP_v35.0 - Surgical Nexus Installation Script
# This script prepares a new node for joining the Hive.

set -e

echo "🧠 [NEXUS] Initializing Hive Node Setup..."

# 1. System Dependencies (Arch Linux focus)
if [ -f /etc/arch-release ]; then
    echo "📦 [NEXUS] Detected Arch Linux. Verifying dependencies..."
    sudo pacman -S --needed --noconfirm python python-pip bubblewrap sqlite lsb-release
fi

# 2. Virtual Environment
if [ ! -d "venv" ]; then
    echo "🐍 [NEXUS] Creating Python Virtual Environment..."
    python3 -m venv venv
fi

# 3. Dependency Injection
echo "💉 [NEXUS] Injecting Python Dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install flask flask-socketio eventlet requests numpy ollama duckduckgo-search

# 4. Directory Structure
echo "📁 [NEXUS] Establishing Neural Paths..."
mkdir -p ~/.native-agent/graffiti

# 5. Environment Template
if [ ! -f ~/.native-agent/.env ]; then
    echo "🔑 [NEXUS] Creating .env template at ~/.native-agent/.env"
    echo "TELEGRAM_BOT_TOKEN=\"\"" > ~/.native-agent/.env
    echo "TELEGRAM_CHAT_ID=\"\"" >> ~/.native-agent/.env
    echo "⚠️  ACTION REQUIRED: Please add your Telegram credentials to ~/.native-agent/.env"
fi

# 6. Systemd Service (Optional but recommended)
SERVICE_PATH="$HOME/.config/systemd/user/swarm-portal.service"
if [ ! -f "$SERVICE_PATH" ]; then
    echo "⚙️  [NEXUS] Installing systemd user service..."
    mkdir -p ~/.config/systemd/user/
    cat <<EOF > "$SERVICE_PATH"
[Unit]
Description=Swarm OS Portal
After=network.target

[Service]
Type=simple
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python3 scripts/ui/web_portal.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload
    echo "✅ [NEXUS] Service installed. Use 'systemctl --user start swarm-portal' to launch."
fi

echo "🚀 [NEXUS] Setup Complete. Neural Core is ready for activation."
