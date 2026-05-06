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

# 5. Create Global Commands
echo "🚀 Creating Global Commands..."

# goku-lite (The Main Orchestrator)
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

sudo chmod +x /usr/local/bin/goku-lite
sudo chmod +x /usr/local/bin/goku-lite-cli
sudo chmod +x /usr/local/bin/goku-lite-setup

echo "✨ Goku Lite Installation Complete!"
echo "------------------------------------------------"
echo "🐉 Run 'goku-lite-setup' to configure your cloud."
echo "🐉 Run 'goku-lite' to start the orchestrator."
echo "🐉 Run 'goku-lite-cli' for terminal chat."
echo "------------------------------------------------"
