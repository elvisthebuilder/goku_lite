import os
import asyncio
import questionary
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from sqlalchemy import create_engine
from qdrant_client import QdrantClient
from dotenv import load_dotenv

console = Console()

def save_to_env(key, value):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    
    new_lines = []
    found = False
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        new_lines.append(f"{key}={value}\n")
    
    try:
        with open(env_path, "w") as f:
            f.writelines(new_lines)
    except PermissionError:
        print(f"❌ Error: Permission denied to write to {env_path}")
        sys.exit(1)

async def test_db(url):
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            return True
    except Exception as e:
        console.print(f"[red]DB Connection Failed:[/] {e}")
        return False

async def test_qdrant(url, key):
    try:
        client = QdrantClient(url=url, api_key=key, timeout=5)
        client.get_collections()
        return True
    except Exception as e:
        console.print(f"[red]Qdrant Connection Failed:[/] {e}")
        return False

# --- Modular Setup Functions ---

async def setup_llm():
    console.print("\n[bold cyan]1. AI Brain Configuration[/]")
    provider = await questionary.select(
        "Choose your Cloud AI Provider:",
        choices=["OpenAI", "Anthropic", "Gemini", "Ollama (Cloud/Remote)"]
    ).ask_async()

    if provider == "OpenAI":
        key = await questionary.password("Enter OpenAI API Key:").ask_async()
        save_to_env("OPENAI_API_KEY", key)
        save_to_env("GOKU_MODEL", "gpt-4o-mini")
    elif provider == "Gemini":
        key = await questionary.password("Enter Google/Gemini API Key:").ask_async()
        save_to_env("GEMINI_API_KEY", key)
        save_to_env("GOKU_MODEL", "gemini/gemini-2.5-flash")
    elif provider == "Anthropic":
        key = await questionary.password("Enter Anthropic API Key:").ask_async()
        save_to_env("ANTHROPIC_API_KEY", key)
        save_to_env("GOKU_MODEL", "claude-3-haiku-20240307")
    elif provider == "Ollama (Cloud/Remote)":
        url = await questionary.text(
            "Enter Ollama API Endpoint (Base URL):", 
            default="https://ollama.com",
            instruction="Tip: Use https://ollama.com for Ollama Cloud (I'll handle the /api part)."
        ).ask_async()
        key = await questionary.password("Enter API Key (Optional):").ask_async()
        model = await questionary.text("Enter Ollama Model Name:", default="ollama/gpt-oss:120b-cloud").ask_async()
        save_to_env("OLLAMA_API_BASE", url)
        if key: save_to_env("OLLAMA_API_KEY", key)
        save_to_env("GOKU_MODEL", model)

async def setup_database():
    console.print("\n[bold cyan]2. Database Configuration (History/Logs)[/]")
    db_url = await questionary.text("Enter PostgreSQL URL:").ask_async()
    if db_url:
        with console.status("Testing Database..."):
            if await test_db(db_url):
                console.print("[green]✅ Database Linked![/]")
                save_to_env("DATABASE_URL", db_url)
            else:
                if await questionary.confirm("Failed. Save anyway?").ask_async():
                    save_to_env("DATABASE_URL", db_url)

async def setup_memory():
    console.print("\n[bold cyan]3. Long-Term Memory (Vector DB)[/]")
    q_url = await questionary.text("Enter Qdrant URL:").ask_async()
    q_key = await questionary.password("Enter Qdrant API Key:").ask_async()
    if q_url and q_key:
        with console.status("Testing Qdrant..."):
            if await test_qdrant(q_url, q_key):
                console.print("[green]✅ Memory Linked![/]")
                save_to_env("QDRANT_URL", q_url)
                save_to_env("QDRANT_API_KEY", q_key)

async def setup_search_voice():
    console.print("\n[bold cyan]4. Web Search & Voice[/]")
    t_key = await questionary.password("Enter Tavily API Key (Optional):").ask_async()
    if t_key: save_to_env("TAVILY_API_KEY", t_key)
    
    e_key = await questionary.password("Enter ElevenLabs API Key (Optional):").ask_async()
    if e_key:
        save_to_env("ELEVENLABS_API_KEY", e_key)
        v_id = await questionary.text("Enter Voice ID (Default: Adam):", default="pNInz6obpg8ndclK7BJb").ask_async()
        save_to_env("ELEVENLABS_VOICE_ID", v_id)

async def setup_channels():
    console.print("\n[bold cyan]5. Messaging Channels[/]")
    tg_token = await questionary.text("Enter Telegram Bot Token (Optional):").ask_async()
    if tg_token: save_to_env("TELEGRAM_BOT_TOKEN", tg_token)
    
    if await questionary.confirm("Enable WhatsApp Bot?").ask_async():
        save_to_env("ENABLE_WHATSAPP", "True")
    else:
        save_to_env("ENABLE_WHATSAPP", "False")
    
    owner_id = await questionary.text("Enter Owner ID (For Exclusive Access):").ask_async()
    if owner_id: save_to_env("GOKU_OWNER_ID", owner_id)

async def setup_security():
    console.print("\n[bold cyan]6. Security Configuration[/]")
    s_key = await questionary.password("Enter API Secret Key (To secure your Web API):").ask_async()
    if s_key: save_to_env("API_SECRET_KEY", s_key)

# --- Main Application Logic ---

async def main():
    console.print(Panel("[bold dragon]🐉 Goku Lite: Cloud Control Center[/]\nManage your Elite Agent's Infrastructure.", border_style="orange3"))

    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    
    if os.path.exists(env_path):
        # Existing Config Menu
        choice = await questionary.select(
            "What would you like to update?",
            choices=[
                "🧠 AI Brain (LLM / Ollama Cloud)",
                "💾 Database (SQL History)",
                "🧠 Memory (Qdrant Cloud)",
                "🌐 Web Search & Voice (Tavily/ElevenLabs)",
                "💬 Messaging Channels (Telegram/WhatsApp)",
                "🔒 Security (API Secret)",
                "✨ Full Re-Setup",
                "❌ Exit"
            ]
        ).ask_async()

        if choice == "🧠 AI Brain (LLM / Ollama Cloud)": await setup_llm()
        elif choice == "💾 Database (SQL History)": await setup_database()
        elif choice == "🧠 Memory (Qdrant Cloud)": await setup_memory()
        elif choice == "🌐 Web Search & Voice (Tavily/ElevenLabs)": await setup_search_voice()
        elif choice == "💬 Messaging Channels (Telegram/WhatsApp)": await setup_channels()
        elif choice == "🔒 Security (API Secret)": await setup_security()
        elif choice == "✨ Full Re-Setup":
            await setup_llm()
            await setup_database()
            await setup_memory()
            await setup_search_voice()
            await setup_channels()
            await setup_security()
        elif choice == "❌ Exit":
            sys.exit(0)
    else:
        # First Time Setup
        console.print("[yellow]No configuration found. Starting Full Onboarding...[/]")
        await setup_llm()
        await setup_database()
        await setup_memory()
        await setup_search_voice()
        await setup_channels()
        await setup_security()

    console.print(Panel("[bold green]✨ Settings Synchronized![/]\nGoku Lite is updated and ready for action.", border_style="green"))

if __name__ == "__main__":
    asyncio.run(main())
