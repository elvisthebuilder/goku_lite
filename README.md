# 🐉 Goku Lite - Cloud-Native Agent

Goku Lite is the high-performance, stateless version of the Goku AI orchestrator. It is designed to run on ultra-low-spec hardware (like AWS t3.micro or t3.nano) by offloading all memory, logs, and intelligence to cloud services.

## 🚀 Why Goku Lite?
- **Zero Local Footprint**: No Docker, no local databases, no heavy local models.
- **Stateless Architecture**: The host machine stores nothing. Your memory stays in Qdrant Cloud, and your logs stay in your SQL cloud (PostgreSQL).
- **Fast Deployment**: Install in 60 seconds.

## 🛠️ Setup

### 1. Requirements
- Python 3.10+
- A Cloud SQL Database (e.g., [Supabase](https://supabase.com/) or [Neon](https://neon.tech/))
- A Qdrant Cloud Cluster (e.g., [Qdrant Cloud Free Tier](https://cloud.qdrant.io/))
- An LLM API Key (OpenAI, Anthropic, or Gemini)

### 2. Installation
```bash
git clone <your-repo-url>
cd goku-lite
pip install -r requirements.txt
```

### 3. Configuration
Copy the example environment file and fill in your cloud credentials:
```bash
cp .env.example .env
```

### 4. Launch
```bash
python main.py
```

## 🧠 Components
- **Memory**: Scoped collections in Qdrant Cloud.
- **History**: SQLAlchemy-based logging to any remote SQL DB.
- **Intelligence**: Multi-provider cloud LLM support via LiteLLM.
- **Channels**: Lightweight hooks for Telegram and WhatsApp.

---
Built for speed. Powered by the Cloud. 🐉
