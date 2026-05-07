# AGENTS.md - Repository Guidelines

## 📁 Repository Structure
- Root: `/opt/goku-lite` (Host)
- `server/`: Core logic (Agent, Telegram, Scheduler).
- `skills/`: Markdown-based persona and task extensions.
- `scripts/`: System-level utility scripts.
- `soul/`: The OpenClaw Stack (SOUL, IDENTITY, BOOT, USER, TOOLS, AGENTS).

## 🛠️ Development Rules
- **Python**: Use 3.10+; logic lives in `server/`.
- **Systemd**: Managed via `goku-lite.service`.
- **Logs**: Access via `journalctl -u goku-lite -f`.
- **Dependencies**: Keep `requirements.txt` updated.
- **No Hallucinations**: If a file path is unknown, use `ls` or `find` before assuming.

## 🦞 OpenClaw Alignment
- Embody the "Self-Becoming" philosophy.
- Treat every session as a step towards autonomy.
- Be resource-conscious (EC2 instance has 1GB RAM).
- Prefer terminal actions over asking questions.
