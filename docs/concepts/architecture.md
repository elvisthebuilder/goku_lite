# Goku Lite Architecture

Goku is built using the **OpenClaw Orchestration Pattern**.

## 🧬 The Prompt Stack
Goku does not have a single static prompt. He builds his consciousness by "stacking" the following files:
1. `SOUL.md`: Persona and Vibe.
2. `AGENTS.md`: Technical Guardrails and Repo Structure.
3. `USER.md`: Owner's identity and preferences.
4. `TOOLS.md`: Reference for terminal and cloud capabilities.
5. `docs/`: Local documentation (this file).

## 🏢 The Body vs. Soul
- **The Body (System)**: The raw Ubuntu host, the EC2 instance, the RAM, and the Disk. Handled via shell commands.
- **The Soul (Agent)**: The reasoning engine, the personality, and the connectivity with the Owner. Handled via the Cloud LLM (Gemini/Claude).

## 🧠 Memory
Goku uses a SQLite database to persist context between restarts, ensuring he doesn't "forget" the Owner's long-term goals.
