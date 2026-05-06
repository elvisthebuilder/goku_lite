import os
import sys
import questionary
from rich.console import Console
from rich.panel import Panel

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
        console.print(f"\n[red]❌ Permission Denied:[/] Cannot write to {env_path}")
        console.print("[yellow]Tip: Try running the command with sudo:[/] [bold]sudo goku-lite-model[/]")
        sys.exit(1)

def main():
    console.print(Panel("[bold dragon]🐉 Goku Lite: Model Switcher[/]\nQuickly swap your AI Cloud Brain.", border_style="cyan"))
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv_path = os.path.join(base_dir, ".env")
    
    current_model = "Unknown"
    if os.path.exists(load_dotenv_path):
        with open(load_dotenv_path, "r") as f:
            for line in f:
                if line.startswith("GOKU_MODEL="):
                    current_model = line.split("=")[1].strip()

    console.print(f"Current Model: [bold yellow]{current_model}[/]")
    
    new_model = questionary.text(
        "Enter new Model ID:",
        default=current_model,
        instruction="e.g. gemini/gemini-2.5-flash, gpt-4o-mini, or ollama/llama3"
    ).ask()

    if new_model:
        save_to_env("GOKU_MODEL", new_model)
        console.print(f"[green]✅ Success! Model updated to: [bold]{new_model}[/][/]")
        console.print("[yellow]Hint: Run 'goku-lite-restart' to apply the change to the background bot.[/]")
    else:
        console.print("[red]Cancelled.[/]")

if __name__ == "__main__":
    main()
