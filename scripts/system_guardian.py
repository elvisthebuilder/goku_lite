import subprocess
import json
import os

def check_health():
    """Deep system health check for an autonomous agent."""
    report = {
        "status": "HEALTHY",
        "issues": [],
        "metrics": {}
    }
    
    # 1. Check DB File
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "goku_lite_fallback.db")
    if os.path.exists(db_path):
        size = os.path.getsize(db_path) / (1024 * 1024)
        report["metrics"]["db_size_mb"] = round(size, 2)
        if size > 500:
            report["issues"].append("DB size is large (>500MB). Consider vacuuming.")
    
    # 2. Check for zombie goku processes
    try:
        ps = subprocess.check_output(["ps", "aux"]).decode()
        goku_procs = [line for line in ps.split("\n") if "main.py" in line]
        report["metrics"]["active_instances"] = len(goku_procs)
        if len(goku_procs) > 2:
            report["issues"].append(f"Multiple instances detected ({len(goku_procs)}). Possible zombie processes.")
    except:
        pass

    if report["issues"]:
        report["status"] = "WARNING"
        
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    check_health()
