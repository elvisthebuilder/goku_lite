import os
import tarfile
import json

def package_skill(skill_dir, output_path):
    """Package a skill directory into a distributable .skill file."""
    print(f"📦 Packaging skill: {skill_dir}...")
    
    with tarfile.open(output_path, "w:gz") as tar:
        tar.add(skill_dir, arcname=os.path.basename(skill_dir))
        
    print(f"✅ Skill packaged successfully: {output_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        package_skill(sys.argv[1], sys.argv[2])
