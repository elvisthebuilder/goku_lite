import asyncio
import json
import os
import time
from datetime import datetime

async def run_test_case(prompt, skill_path=None, output_dir="outputs"):
    """
    Simulate an execution run for a specific eval prompt.
    Captures timing, tokens, and outputs.
    """
    os.makedirs(output_dir, exist_ok=True)
    start_time = time.time()
    
    # In a real scenario, this would call CloudAgent.chat()
    # For now, we simulate the execution metadata
    print(f"🚀 Running Eval: '{prompt[:50]}...' {'(With Skill)' if skill_path else '(Baseline)'}")
    
    # Simulate work
    await asyncio.sleep(2) 
    
    duration = time.time() - start_time
    
    # Save Timing
    timing = {
        "total_duration_seconds": round(duration, 2),
        "total_tokens": 1200 # Mock data
    }
    with open(os.path.join(output_dir, "..", "timing.json"), "w") as f:
        json.dump(timing, f, indent=2)
        
    print(f"✅ Run complete in {round(duration, 2)}s")

if __name__ == "__main__":
    # Example usage
    asyncio.run(run_test_case("Verify system memory", output_dir="workspace/iteration-1/eval-0/with_skill/outputs"))
