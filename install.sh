#!/bin/bash

# 🐉 Goku Lite Installer
# Built by Elvis The Builder

set -e

echo "🐉 Goku Lite: Starting Elite Installation..."

# 1. System Check
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    exit 1
fi

# 2. Setup Directory
INSTALL_DIR="/opt/goku-lite"
echo "📂 Installing to $INSTALL_DIR..."
sudo mkdir -p $INSTALL_DIR
sudo cp -r . $INSTALL_DIR
sudo chown -R $USER:$USER $INSTALL_DIR

cd $INSTALL_DIR

# 3. Virtual Environment
echo "🐍 Setting up Virtual Environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Dependencies
echo "📦 Installing Cloud-Native Dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Create Systemd Service
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

# 6. Create Global Commands
echo "🚀 Creating Global Commands..."

# goku-lite (Direct foreground run)
cat <<EOF | sudo tee /usr/local/bin/goku-lite > /dev/null
#!/bin/bash
cd $INSTALL_DIR
source venv/bin/activate
python3 main.py "\$@"
EOF

# goku-lite-cli (The CLI Chat)
cat <<EOF | sudo tee /usr/local/bin/goku-lite-cli > /dev/null
#!/bin/bash
cd $INSTALL_DIR
source venv/bin/activate
python3 cli.py "\$@"
EOF

# goku-lite-setup (The Onboarding Wizard)
cat <<EOF | sudo tee /usr/local/bin/goku-lite-setup > /dev/null
#!/bin/bash
cd $INSTALL_DIR
source venv/bin/activate
python3 setup.py
EOF

# goku-lite-start (Start Background)
cat <<EOF | sudo tee /usr/local/bin/goku-lite-start > /dev/null
#!/bin/bash
sudo systemctl start goku-lite
echo "🐉 Goku Lite is now active in the background."
EOF

# goku-lite-stop (Stop Background)
cat <<EOF | sudo tee /usr/local/bin/goku-lite-stop > /dev/null
#!/bin/bash
sudo systemctl stop goku-lite
echo "🛑 Goku Lite has been stopped."
EOF

# goku-lite-restart (Restart Background)
cat <<EOF | sudo tee /usr/local/bin/goku-lite-restart > /dev/null
#!/bin/bash
sudo systemctl restart goku-lite
echo "🔄 Goku Lite has been restarted."
EOF

# goku-lite-logs (Watch Logs)
cat <<EOF | sudo tee /usr/local/bin/goku-lite-logs > /dev/null
#!/bin/bash
sudo journalctl -u goku-lite -f
EOF

sudo chmod +x /usr/local/bin/goku-lite*

echo "✨ Goku Lite Installation Complete!"
echo "------------------------------------------------"
echo "🐉 Setup:    goku-lite-setup"
echo "🐉 Start:    goku-lite-start"
echo "🐉 Stop:     goku-lite-stop"
echo "🐉 Restart:  goku-lite-restart"
echo "🐉 Logs:     goku-lite-logs"
echo "🐉 Chat:     goku-lite-cli"
echo "------------------------------------------------"
