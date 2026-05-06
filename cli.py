import asyncio
from server.agent import agent
from server.config import config
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
    table.add_row("/exit", "Close the CLI")
    console.print(table)

def show_status():
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
    
    config.validate()
    session_id = "cli_session"
    
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
                    show_status()
                elif cmd == "/setup":
                    import subprocess
                    subprocess.run(["python3", "setup.py"])
                elif cmd in ["/exit", "/quit"]:
                    break
                else:
                    console.print(f"[bold red]Unknown command:[/] {cmd}")
                continue

            # Default: Chat
            with console.status("[bold yellow]Goku is thinking...[/]"):
                response = await agent.chat(user_input, session_id=session_id, source="cli")
            
            console.print(f"[bold orange3]Goku >[/] {response}\n")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/] {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
