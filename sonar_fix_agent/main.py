import os
import tempfile
import json
from pathlib import Path
from collections import defaultdict
from .config import GITHUB_TOKEN
from .sonar_client import fetch_issues
from .github_client import get_github_repo, create_pr
from .llm_fixer import generate_patch
from .validator import run

# Maximum number of fixes per PR
MAX_FIXES_PER_PR = 3
FIXED_KEYS_FILE = ".fixed_issues.json"

def main():
    repo_full = os.getenv("GITHUB_REPOSITORY")
    if not repo_full:
        print("Set GITHUB_REPOSITORY env var (e.g., user/repo)")
        return

    # Get repo object from GitHub
    repo = get_github_repo(GITHUB_TOKEN, repo_full)

    # Setup temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{repo_full}.git"
        print(f"Cloning repo {repo_full} into {tmpdir}")
        run(["git", "clone", clone_url, tmpdir])

        # Configure git
        run(["git", "config", "user.name", "github-actions[bot]"], cwd=tmpdir)
        run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], cwd=tmpdir)
        run(["git", "checkout", "-b", "bot/sonar-fixes"], cwd=tmpdir)

        # Fetch all Sonar issues
        project_key = repo_full.replace("/", ":")
        issues = fetch_issues(project_key)
        if not issues:
            print("✅ No Sonar issues found in project.")
            return

        print(f"🔍 Found {len(issues)} issues in Sonar.")

        # Load fixed keys to avoid duplicates
        fixed_keys_path = Path(tmpdir)/FIXED_KEYS_FILE
        if fixed_keys_path.exists():
            fixed_keys = json.load(fixed_keys_path)
        else:
            fixed_keys = []

        # Filter out already fixed issues
        issues_to_fix = [i for i in issues if i["key"] not in fixed_keys]

        if not issues_to_fix:
            print("✅ All issues already fixed in previous runs.")
            return

        # Categorize issues by severity
        issues_by_severity = defaultdict(list)
        for issue in issues_to_fix:
            sev = issue.get("severity", "MINOR")
            issues_by_severity[sev].append(issue)

        # Pick top issues by severity
        targets = []
        for sev in ["BLOCKER", "CRITICAL", "MAJOR", "MINOR"]:
            targets.extend(issues_by_severity.get(sev, []))
        targets = targets[:MAX_FIXES_PER_PR]

        print(f"🛠️ Preparing to fix {len(targets)} issues in this run.")

        changed_files = set()
        pr_summary = []

        for issue in targets:
            file_path = Path(tmpdir)/"/".join(issue["component"].split(":")[1:])
            if not file_path.exists():
                print(f"⚠️ Skipping {issue['component']} (file not found).")
                continue

            code = file_path.read_text(encoding="utf-8", errors="ignore")
            patch = generate_patch(str(file_path), code, issue["rule"], issue["message"])
            if not patch:
                print(f"⚠️ No patch generated for {file_path}")
                continue

            patch_file = Path(tmpdir)/".tmp.patch"
            patch_file.write_text(patch)

            try:
                run(["git", "apply", "--whitespace=fix", str(patch_file)], cwd=tmpdir)
                changed_files.add(file_path)
                pr_summary.append(f"- {issue['severity']}: {issue['message']} in {issue['component']}")
                fixed_keys.append(issue["key"])
                print(f"✅ Applied patch for {file_path}")
            except Exception as e:
                print(f"❌ Failed to apply patch for {file_path}: {e}")
                run(["git", "checkout", "--", str(file_path)], cwd=tmpdir)

        if not changed_files:
            print("⚠️ No fixes were applied in this run.")
            return

        # Commit changes
        run(["git", "add", "-A"], cwd=tmpdir)
        run(["git", "commit", "-m", "fix(sonar): apply automated fixes"], cwd=tmpdir)
        run(["git", "push", "--set-upstream", "origin", "bot/sonar-fixes"], cwd=tmpdir)

        # Save updated fixed keys
        json.dump(fixed_keys, fixed_keys_path)

        # Create PR with summary
        pr_title = "fix(sonar): automated fixes"
        pr_body = "This PR fixes the following SonarQube issues:\n\n" + "\n".join(pr_summary)
        pr_number = create_pr(repo, "bot/sonar-fixes", pr_title, pr_body)
        print(f"🚀 Opened PR #{pr_number} with {len(targets)} fixes.")

if __name__ == "__main__":
    main()
