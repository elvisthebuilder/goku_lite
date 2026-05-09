import os
import sys
import subprocess
import asyncio

# Get the absolute path to the directory where this script is located
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, ".env")

from dotenv import load_dotenv
load_dotenv(env_path)

# Guard: Ensure configuration exists
if not os.path.exists(env_path) or not os.getenv("GOKU_MODEL"):
    print("🐉 Goku Lite: Missing configuration. Launching Onboarding Wizard...")
    try:
        setup_script = os.path.join(base_dir, "setup.py")
        result = subprocess.run([sys.executable, setup_script])
        if result.returncode != 0:
            print("\n[red]🛑 Setup was cancelled or failed. Goku cannot start without configuration.[/]")
            sys.exit(1)
        load_dotenv(env_path, override=True)
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def show_help():
    table = Table(title="🐉 Goku Lite Commands", show_header=True, header_style="bold magenta")
    table.add_column("Command", style="cyan")
    table.add_column("Description")
    table.add_row("/help", "Show this help menu")
    table.add_row("/status", "Check Cloud Connectivity (Memory/DB/LLM)")
    table.add_row("/setup", "Run the Configuration Wizard")
    table.add_row("/reset", "Wipe all memories and history (Tabula Rasa)")
    table.add_row("/update", "Pull the latest updates from GitHub")
    table.add_row("/exit", "Close the CLI")
    console.print(table)

def show_status(config):
    table = Table(title="🌐 Cloud Infrastructure Status", show_header=True)
    table.add_column("Service", style="bold")
    table.add_column("Status")
    
    # Check DB
    db_status = "[bold green]ONLINE (External)[/]" if config.DATABASE_URL else "[bold yellow]FALLBACK (SQLite)[/]"
    table.add_row("Database (SQL)", db_status)
    
    # Check Memory
    mem_status = "[bold green]ONLINE (Qdrant Cloud)[/]" if config.QDRANT_API_KEY else "[bold red]OFFLINE[/]"
    table.add_row("Memory (Vector)", mem_status)
    
    # Check LLM
    llm_status = f"[bold green]READY ({config.GOKU_MODEL})[/]" if config.OPENAI_API_KEY or config.GEMINI_API_KEY or config.ANTHROPIC_API_KEY else "[bold red]MISSING KEYS[/]"
    table.add_row("Intelligence (LLM)", llm_status)
    
    console.print(table)

async def main():
    console.print(Panel("[bold red]🐉 Goku Lite CLI[/]\n[italic]The Cloud-Native Orchestrator[/]\nType '/help' for commands.", border_style="orange3"))

    # Lazy-load heavy dependencies AFTER the banner is shown
    with console.status("[dim]Loading intelligence engine...[/]", spinner="dots"):
        from server.agent import agent
        from server.config import config

    config.validate()
    session_id = "cli_session"

    # 2. Interactive Loop
    while True:
        try:
            user_input = console.input("[bold cyan]You > [/]").strip()
            
            if not user_input:
                continue
            
            # Command Handler
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd == "/help":
                    show_help()
                elif cmd == "/status":
                    show_status(config)
                elif cmd == "/setup":
                    import subprocess
                    subprocess.run(["python3", "setup.py"])
                elif cmd == "/reset":
                    console.print("[bold red]⚠️  WARNING:[/] To perform a total reset (wiping all memory and history), exit this CLI and run:")
                    console.print("[bold cyan]python3 scripts/total_reset.py[/]")
                elif cmd == "/update":
                    console.print("[bold cyan]🔄 To update Goku Lite to the latest version, exit this CLI and run:[/]")
                    console.print("[bold cyan]goku-lite-update[/]")
                elif cmd in ["/exit", "/quit"]:
                    break
                else:
                    console.print(f"[bold red]Unknown command:[/] {cmd}")
                continue

            # Default: Chat
            from rich.live import Live
            
            with console.status("[bold yellow]Goku is thinking...[/]") as status:
                generator = agent.chat(user_input, session_id=session_id, source="cli")
                
            async for response in generator:
                if response:
                    import re
                    # Extract thinking blocks
                    thinking_match = re.search(r'<think>(.*?)</think>', response, re.DOTALL)
                    clean_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
                    
                    # 1. Flash the Thought Box (Transient)
                    if thinking_match:
                        thought_content = thinking_match.group(1).strip()
                        if thought_content:
                            # We use a nested Live display to show the thoughts temporarily
                            with Live(Panel(
                                thought_content, 
                                title="[dim]Cognitive Stream[/]", 
                                border_style="dim", 
                                subtitle="[dim]Internal reasoning[/]",
                                style="italic dim"
                            ), transient=True, console=console):
                                # Brief pause so the user can see the "Cognitive Gear" turn
                                await asyncio.sleep(1.5)
                    
                    # 2. Render the Final Response (Permanent)
                    if clean_response and clean_response != "∅":
                        console.print(Panel(clean_response, title="[bold dragon]Goku[/]", border_style="cyan"))
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/] {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
