import os
import asyncio
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from sqlalchemy import create_engine
from qdrant_client import QdrantClient
import httpx

console = Console()

def save_to_env(key, value):
    env_path = ".env"
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    
    new_lines = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
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
        print(f"💡 Try running: sudo chown -R $USER:$USER {os.path.dirname(os.path.abspath(env_path))}")
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

async def main():
    console.print(Panel("[bold dragon]🐉 Goku Lite: Comprehensive Cloud Onboarding[/]\nConfigure your Elite Agent's Cloud Infrastructure.", border_style="orange3"))

    # 1. AI Brain (LLM)
    console.print("\n[bold cyan]1. AI Brain Configuration[/]")
    provider = await questionary.select(
        "Choose your Cloud AI Provider:",
        choices=["OpenAI", "Anthropic", "Gemini", "Ollama (Remote)"]
    ).ask_async()

    if provider == "OpenAI":
        key = await questionary.password("Enter OpenAI API Key:").ask_async()
        save_to_env("OPENAI_API_KEY", key)
        save_to_env("GOKU_MODEL", "gpt-4o-mini")
    elif provider == "Gemini":
        key = await questionary.password("Enter Google/Gemini API Key:").ask_async()
        save_to_env("GEMINI_API_KEY", key)
        save_to_env("GOKU_MODEL", "gemini/gemini-2.5-flash")
        console.print("[yellow]💡 Note: Gemini enables Native Google Search for real-time facts.[/]")
    elif provider == "Anthropic":
        key = await questionary.password("Enter Anthropic API Key:").ask_async()
        save_to_env("ANTHROPIC_API_KEY", key)
        save_to_env("GOKU_MODEL", "claude-3-haiku-20240307")
    elif provider == "Ollama (Remote)":
        url = await questionary.text("Enter Ollama Base URL:", default="http://localhost:11434").ask_async()
        key = await questionary.password("Enter API Key (Optional):").ask_async()
        model = await questionary.text("Enter Ollama Model Name:", default="llama3").ask_async()
        save_to_env("OLLAMA_API_BASE", url)
        if key: save_to_env("OLLAMA_API_KEY", key)
        save_to_env("GOKU_MODEL", f"ollama/{model}")

    # 2. Database (PostgreSQL)
    console.print("\n[bold cyan]2. Database Configuration (History/Logs)[/]")
    if await questionary.confirm("Configure External SQL Database? (Recommended for cloud)").ask_async():
        db_url = await questionary.text("Enter PostgreSQL URL:").ask_async()
        if db_url:
            with console.status("Testing Database..."):
                if await test_db(db_url):
                    console.print("[green]✅ Database Linked![/]")
                    save_to_env("DATABASE_URL", db_url)
                else:
                    if await questionary.confirm("Failed. Save anyway?").ask_async():
                        save_to_env("DATABASE_URL", db_url)

    # 3. Memory (Qdrant Cloud)
    console.print("\n[bold cyan]3. Long-Term Memory (Vector DB)[/]")
    if await questionary.confirm("Configure Qdrant Cloud Memory?").ask_async():
        q_url = await questionary.text("Enter Qdrant URL:").ask_async()
        q_key = await questionary.password("Enter Qdrant API Key:").ask_async()
        if q_url and q_key:
            with console.status("Testing Qdrant..."):
                if await test_qdrant(q_url, q_key):
                    console.print("[green]✅ Memory Linked![/]")
                    save_to_env("QDRANT_URL", q_url)
                    save_to_env("QDRANT_API_KEY", q_key)

    # 4. Search (Tavily)
    console.print("\n[bold cyan]4. Web Search Configuration[/]")
    t_key = await questionary.password("Enter Tavily API Key (Optional):").ask_async()
    if t_key:
        save_to_env("TAVILY_API_KEY", t_key)

    # 5. Voice (ElevenLabs)
    console.print("\n[bold cyan]5. Voice Synthesis (ElevenLabs)[/]")
    e_key = await questionary.password("Enter ElevenLabs API Key (Optional):").ask_async()
    if e_key:
        save_to_env("ELEVENLABS_API_KEY", e_key)
        v_id = await questionary.text("Enter Voice ID (Default: Adam):", default="pNInz6obpg8ndclK7BJb").ask_async()
        save_to_env("ELEVENLABS_VOICE_ID", v_id)

    # 6. Messaging Channels
    console.print("\n[bold cyan]6. Messaging Channels[/]")
    tg_token = await questionary.text("Enter Telegram Bot Token (Optional):").ask_async()
    if tg_token:
        save_to_env("TELEGRAM_BOT_TOKEN", tg_token)
    
    if await questionary.confirm("Enable WhatsApp Bot?").ask_async():
        save_to_env("ENABLE_WHATSAPP", "True")
    else:
        save_to_env("ENABLE_WHATSAPP", "False")
    
    owner_id = await questionary.text("Enter Owner ID (For Exclusive Access):").ask_async()
    if owner_id:
        save_to_env("GOKU_OWNER_ID", owner_id)

    # 7. Security
    console.print("\n[bold cyan]7. Security Configuration[/]")
    s_key = await questionary.password("Enter API Secret Key (To secure your Web API):").ask_async()
    if s_key:
        save_to_env("API_SECRET_KEY", s_key)

    console.print(Panel("[bold green]✨ All Cloud Systems Go![/]\nGoku Lite is now fully synchronized and ready for production.", border_style="green"))

if __name__ == "__main__":
    asyncio.run(main())
