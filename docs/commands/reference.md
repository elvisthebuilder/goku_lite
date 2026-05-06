# Command Reference

Goku Lite supports the following commands across Telegram and CLI.

## 📱 Telegram Commands
- `/start`: Initialize the session and greet the owner.
- `/new`: Wipe the current session history and "re-read" the Soul into existence.
- `/status`: Run a real-time health check (RAM, Disk, Uptime).
- `/briefing`: Generate a situational report (System + Brain status).
- `/help`: Display this reference guide.

## 🐚 CLI Commands
- `python3 main.py`: Start the agent in interactive CLI mode.
- `goku-lite-logs`: (Alias) Stream the system logs.
- `goku-lite-restart`: (Alias) Restart the background service.

## 🛠️ Internal Tools
- `read`: Read file contents.
- `write`: Create or overwrite files.
- `exec`: Run shell commands on the Ubuntu host.
- `memory`: Access the SQLite long-term memory.
