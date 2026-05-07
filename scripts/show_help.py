from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def show_help():
    console.print(Panel(
        "[bold dragon]🐉 Goku Lite: Global Command Center[/]\n"
        "Your Elite AI Agent's Management Suite",
        border_style="orange3"
    ))

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    table.add_row("goku-lite-cli", "Open the interactive chat terminal (Shortcut: [bold]goku[/])")
    table.add_row("goku-lite-setup", "Run the infrastructure configuration wizard")
    table.add_row("goku-lite-update", "Pull latest code and refresh dependencies (Sudo-aware)")
    table.add_row("goku-lite-total-reset", "Wipe all chat history and long-term memories")
    table.add_row("goku-lite-start", "Start the Goku Lite background service")
    table.add_row("goku-lite-stop", "Stop the Goku Lite background service")
    table.add_row("goku-lite-restart", "Restart the Goku Lite background service")
    table.add_row("goku-lite-logs", "Tail the live system logs")
    table.add_row("goku-lite-help", "Show this help menu")

    console.print(table)
    console.print("\n[dim]Goku Lite is a cloud-native agent orchestrator built for AWS EC2.[/]")

if __name__ == "__main__":
    show_help()
