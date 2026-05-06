#!/bin/bash

# 🐉 Goku Lite Installer [v1.0.4 - Production]
# Built by Elvis The Builder

set -e

echo "🐉 Goku Lite [v1.0.4]: Starting Force Installation..."

# 1. Force Clean State (Required for Production reliability)
INSTALL_DIR="/opt/goku-lite"
echo "🧹 Cleaning existing installation at $INSTALL_DIR..."
# Delete contents but keep the directory to avoid "ghost directory" errors
sudo find "$INSTALL_DIR" -mindepth 1 -delete || true

# 2. System Dependencies
echo "🛠️  Installing System Dependencies (python3-venv, ffmpeg, git)..."
sudo apt-get update
sudo apt-get install -y python3-venv ffmpeg git python3-pip

# 3. Setup Directory & Clone
echo "📂 Creating directory and cloning fresh from GitHub..."
sudo mkdir -p "$INSTALL_DIR"
sudo git clone https://github.com/elvisthebuilder/goku_lite.git "$INSTALL_DIR"

sudo chown -R $USER:$USER $INSTALL_DIR
cd $INSTALL_DIR

# 4. Virtual Environment
echo "🐍 Setting up Virtual Environment..."
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
sudo apt-get install -y "python3.$PY_VER-venv" || true

python3 -m venv venv
source venv/bin/activate

# 5. Dependencies
echo "📦 Installing Cloud-Native Dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 6. Create Systemd Service
echo "⚙️  Configuring Background Service..."
cat <<EOF | sudo tee /etc/systemd/system/goku-lite.service > /dev/null
[Unit]
Description=Goku Lite AI Orchestrator
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable goku-lite || true

# 7. Create Global Commands
echo "🚀 Creating Global Commands..."

create_global_cmd() {
    local cmd_name=$1
    local script_name=$2
    cat <<EOF | sudo tee /usr/local/bin/$cmd_name > /dev/null
#!/bin/bash
cd $INSTALL_DIR
source venv/bin/activate
python3 $script_name "\$@"
EOF
    sudo chmod +x /usr/local/bin/$cmd_name
}

create_global_cmd "goku-lite" "main.py"
create_global_cmd "goku-lite-cli" "cli.py"
create_global_cmd "goku" "cli.py"
create_global_cmd "goku-lite-setup" "setup.py"
create_global_cmd "goku-lite-wizard" "setup.py"

# Management Helpers
cat <<EOF | sudo tee /usr/local/bin/goku-lite-start > /dev/null
#!/bin/bash
sudo systemctl start goku-lite
echo "🐉 Goku Lite is now active in the background."
EOF

cat <<EOF | sudo tee /usr/local/bin/goku-lite-stop > /dev/null
#!/bin/bash
sudo systemctl stop goku-lite
echo "🛑 Goku Lite has been stopped."
EOF

cat <<EOF | sudo tee /usr/local/bin/goku-lite-restart > /dev/null
#!/bin/bash
sudo systemctl restart goku-lite
echo "🔄 Goku Lite has been restarted."
EOF

cat <<EOF | sudo tee /usr/local/bin/goku-lite-logs > /dev/null
#!/bin/bash
sudo journalctl -u goku-lite -f
EOF

sudo chmod +x /usr/local/bin/goku-lite*

echo "✨ Goku Lite [v1.0.4] Installation Complete!"
echo "------------------------------------------------"
echo "🐉 Setup:    goku-lite-setup"
echo "🐉 Start:    goku-lite-start"
echo "🐉 Stop:     goku-lite-stop"
echo "🐉 Restart:  goku-lite-restart"
echo "🐉 Logs:     goku-lite-logs"
echo "🐉 Chat:     goku-lite-cli"
echo "------------------------------------------------"
