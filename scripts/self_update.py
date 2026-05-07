import subprocess
import os
import sys
from rich.console import Console
from rich.panel import Panel

console = Console()

def update_goku():
    """Safely pull updates, refresh dependencies, and restart services with elevated permissions."""
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    console.print(Panel(
        "[bold cyan]🐉 Goku Lite: Autonomous Update Sequence[/]\n"
        f"Target Directory: {repo_dir}",
        border_style="cyan"
    ))
    
    try:
        # 1. Pull from Git (using sudo if permissions fail)
        console.print("[yellow]📥 Pulling fresh code from GitHub...[/]")
        try:
            subprocess.run(["git", "pull", "origin", "main"], cwd=repo_dir, check=True)
        except subprocess.CalledProcessError:
            console.print("[dim]Standard pull failed. Retrying with sudo...[/]")
            subprocess.run(["sudo", "git", "pull", "origin", "main"], cwd=repo_dir, check=True)
        
        # 2. Update dependencies
        console.print("[yellow]📦 Refreshing cloud dependencies...[/]")
        venv_pip = os.path.join(repo_dir, "venv", "bin", "pip")
        requirements = os.path.join(repo_dir, "requirements.txt")
        
        if os.path.exists(venv_pip) and os.path.exists(requirements):
            try:
                subprocess.run([venv_pip, "install", "-r", requirements], check=True)
            except subprocess.CalledProcessError:
                console.print("[dim]Standard pip install failed. Retrying with sudo...[/]")
                subprocess.run(["sudo", venv_pip, "install", "-r", requirements], check=True)
        else:
            console.print("[dim]Skipping dependency update (no venv found).[/]")
        
        # 3. Restart via systemctl
        console.print("[yellow]🚀 Restarting Goku Lite background service...[/]")
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "restart", "goku-lite"], check=True)
        
        console.print(Panel(
            "[bold green]✅ Update Successful![/]\n"
            "Goku Lite has been updated and the service has been restarted.",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(Panel(
            f"[bold red]❌ Update Failed[/]\n{str(e)}",
            border_style="red"
        ))
        sys.exit(1)

if __name__ == "__main__":
    update_goku()
