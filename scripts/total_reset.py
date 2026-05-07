import os
import sys
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

# Add parent dir to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.history import history
from server.memory import memory
from server.config import config

console = Console()

async def total_reset():
    console.print(Panel(
        "[bold red]☢️  TOTAL SYSTEM RESET ☢️[/]\n\n"
        "This command will PERMANENTLY delete:\n"
        "- All Chat History (Neon SQL)\n"
        "- All Long-Term Memories (Qdrant Vector)\n"
        "- All Protected Memories\n"
        "- All User Sessions\n\n"
        "[bold yellow]Your .env configuration will be preserved.[/]",
        border_style="red"
    ))

    # Double Confirmation
    if not Confirm.ask("[bold red]Are you absolutely sure you want to wipe Goku's soul?[/]"):
        console.print("[yellow]Reset cancelled. Goku's memories remain intact.[/]")
        return

    if not Confirm.ask("[bold red]CRITICAL: This cannot be undone. Proceed?[/]"):
        console.print("[yellow]Reset cancelled. Safety first.[/]")
        return

    console.print("\n[bold yellow]Initiating Wipe Sequence...[/]")

    # 1. Reset SQL Database (Neon)
    try:
        with console.status("[cyan]Wiping SQL Database (History/Sessions)...[/]"):
            history.wipe_all_data()
        console.print("[green]✅ SQL History Cleared.[/]")
    except Exception as e:
        console.print(f"[red]❌ SQL Wipe Failed:[/] {e}")

    # 2. Reset Vector Memory (Qdrant)
    try:
        with console.status("[cyan]Wiping Qdrant Cloud (Long-Term Memory)...[/]"):
            success = await memory.clear_all_memory(delete_protected=True)
            if success:
                console.print("[green]✅ Vector Memory Cleared (including protected).[/]")
            else:
                console.print("[yellow]⚠️  Vector Memory Wipe reported failure or was skipped.[/]")
    except Exception as e:
        console.print(f"[red]❌ Qdrant Wipe Failed:[/] {e}")

    console.print(Panel(
        "[bold green]✨ TABULA RASA COMPLETE[/]\n\n"
        "Goku has been reset to a blank slate.\n"
        "The next time you speak to him, he will wake up as if for the first time.",
        border_style="green"
    ))

if __name__ == "__main__":
    try:
        asyncio.run(total_reset())
    except KeyboardInterrupt:
        console.print("\n[red]Reset Interrupted.[/]")
        sys.exit(1)
