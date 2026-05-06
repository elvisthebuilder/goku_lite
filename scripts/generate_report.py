import json
import os

def generate_report(benchmark_json_path, output_md_path):
    """Generate a human-readable Markdown report from benchmark data."""
    if not os.path.exists(benchmark_json_path):
        print(f"❌ Error: {benchmark_json_path} not found.")
        return

    with open(benchmark_json_path, "r") as f:
        data = json.load(f)

    report = [
        "# 📊 Skill Benchmark Report",
        f"Generated on: {os.path.basename(benchmark_json_path)}",
        "",
        "## Summary",
        f"- **Pass Rate:** {data.get('pass_rate', 0) * 100}%",
        f"- **Avg Duration:** {data.get('avg_duration_s', 0)}s",
        f"- **Total Tokens:** {data.get('total_tokens', 0)}",
        "",
        "## Detailed Results",
        "| Eval ID | Pass/Fail | Duration | Tokens |",
        "|---------|-----------|----------|--------|"
    ]
    
    # Logic to populate table from data
    
    with open(output_md_path, "w") as f:
        f.write("\n".join(report))
        
    print(f"📄 Report generated: {output_md_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        generate_report(sys.argv[1], sys.argv[2])
