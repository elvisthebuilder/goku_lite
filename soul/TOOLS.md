# TOOLS.md - Terminal Capabilities

## 🐚 Shell Access
- You have a full PTY-enabled bash shell.
- Use `ls`, `grep`, `find`, and `cat` to explore the repository.
- Use `pip` inside the `venv` to manage packages.

## 📊 System Monitoring
- Use `free -h` for memory.
- Use `df -h` for storage.
- Use `top -b -n 1` for process peaks.

## 🔄 Service Management
- The main service is `goku-lite.service`.
- Commands: `sudo systemctl status goku-lite`, `sudo systemctl restart goku-lite`.
- Use the `goku-lite-logs` alias to see real-time traffic.

## 🧠 Memory Engine
- You have a SQLite-backed memory engine.
- Use it to store facts about the Owner's NBA interests or specific coding patterns we've discussed.
