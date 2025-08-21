import subprocess
from pathlib import Path

def run(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(result.stderr or result.stdout)
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout

def validate_repo(repo_dir):
    try:
        if (Path(repo_dir)/"pom.xml").exists():
            print("🔧 Running mvn verify to validate repository...")
            run(["mvn", "verify"], cwd=repo_dir)
        return True
    except Exception as e:
        print("⚠️ Validation failed:", e)
        return False
