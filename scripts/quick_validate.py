import os
import sys

def validate_skill(skill_path):
    """Quickly validate a skill's structure and frontmatter."""
    if not os.path.exists(skill_path):
        print(f"❌ Error: {skill_path} does not exist.")
        return False
        
    with open(skill_path, "r") as f:
        content = f.read()
        
    issues = []
    # 1. Check for YAML frontmatter
    if not content.startswith("---"):
        issues.append("Missing YAML frontmatter (---)")
        
    # 2. Check for required fields
    if "name:" not in content:
        issues.append("Missing 'name' field in frontmatter")
    if "description:" not in content:
        issues.append("Missing 'description' field in frontmatter")
        
    # 3. Check for body sections
    if "## Instructions" not in content and "## Workflow" not in content:
        issues.append("Missing '## Instructions' or '## Workflow' section")
        
    if issues:
        print(f"⚠️ Validation issues found in {os.path.basename(skill_path)}:")
        for issue in issues:
            print(f"  - {issue}")
        return False
        
    print(f"✅ {os.path.basename(skill_path)} is valid and ready for benchmarking.")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        validate_skill(sys.argv[1])
