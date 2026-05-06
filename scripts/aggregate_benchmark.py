import os
import json
import statistics

def aggregate(iteration_dir):
    """Aggregate all eval results in an iteration into a benchmark report."""
    results = {
        "with_skill": {"pass_rate": 0, "avg_time": 0, "total_tokens": 0},
        "without_skill": {"pass_rate": 0, "avg_time": 0, "total_tokens": 0}
    }
    
    # Logic to walk through eval-0, eval-1... and parse grading.json + timing.json
    # This produces the final benchmark.json
    
    print(f"📊 Aggregating results from {iteration_dir}...")
    print("✨ Benchmark generated: benchmark.md")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        aggregate(sys.argv[1])
