import subprocess
import os

def update_goku():
    """Safely pull updates and restart services."""
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"🔄 Starting Autonomous Update in {repo_dir}...")
    
    try:
        # 1. Pull from Git
        subprocess.run(["git", "pull", "origin", "main"], cwd=repo_dir, check=True)
        
        # 2. Restart via systemctl (if running as service)
        print("🚀 Restarting Goku service...")
        subprocess.run(["sudo", "systemctl", "restart", "goku-lite"], check=True)
        
        print("✅ Update successful.")
    except Exception as e:
        print(f"❌ Update failed: {e}")

if __name__ == "__main__":
    update_goku()
