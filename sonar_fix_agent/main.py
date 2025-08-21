import os
import tempfile
import json
from pathlib import Path
from collections import defaultdict
from .config import GITHUB_TOKEN, MAX_FIXES_PER_PR
from .sonar_client import fetch_issues
from .github_client import get_github_repo, create_pr
from .llm_fixer import generate_patch
from .validator import run

FIXED_KEYS_FILE = ".fixed_issues.json"

def main():
    repo_full = os.getenv("GITHUB_REPOSITORY")
    if not repo_full:
        print("Set GITHUB_REPOSITORY env var (user/repo)")
        return

    repo = get_github_repo(GITHUB_TOKEN, repo_full)
    with tempfile.TemporaryDirectory() as tmpdir:
        clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{repo_full}.git"
        run(["git", "clone", clone_url, tmpdir])
        run(["git", "config", "user.name", "github-actions[bot]"], cwd=tmpdir)
        run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], cwd=tmpdir)
        run(["git", "checkout", "-b", "bot/sonar-fixes"], cwd=tmpdir)

        project_key = repo_full.replace("/", ":")
        issues = fetch_issues(project_key)
        if not issues:
            print("✅ No Sonar issues found.")
            return

        fixed_keys_path = Path(tmpdir)/FIXED_KEYS_FILE
        fixed_keys = json.load(fixed_keys_path) if fixed_keys_path.exists() else []

        issues_to_fix = [i for i in issues if i["key"] not in fixed_keys]
        if not issues_to_fix:
            print("✅ All issues already fixed.")
            return

        issues_by_severity = defaultdict(list)
        for issue in issues_to_fix:
            sev = issue.get("severity", "MINOR")
            issues_by_severity[sev].append(issue)

        targets = []
        for sev in ["BLOCKER", "CRITICAL", "MAJOR", "MINOR"]:
            targets.extend(issues_by_severity.get(sev, []))
        targets = targets[:MAX_FIXES_PER_PR]

        changed_files = set()
        pr_summary = []

        for issue in targets:
            file_path = Path(tmpdir)/"/".join(issue["component"].split(":")[1:])
            if not file_path.exists():
                continue

            code = file_path.read_text(encoding="utf-8", errors="ignore")
            patch = generate_patch(str(file_path), code, issue["rule"], issue["message"])
            if not patch:
                continue

            patch_file = Path(tmpdir)/".tmp.patch"
            patch_file.write_text(patch)

            try:
                run(["git", "apply", "--whitespace=fix", str(patch_file)], cwd=tmpdir)
                changed_files.add(file_path)
                pr_summary.append(f"- {issue['severity']}: {issue['message']} in {issue['component']}")
                fixed_keys.append(issue["key"])
            except Exception:
                run(["git", "checkout", "--", str(file_path)], cwd=tmpdir)

        if not changed_files:
            print("⚠️ No fixes applied.")
            return

        run(["git", "add", "-A"], cwd=tmpdir)
        run(["git", "commit", "-m", "fix(sonar): apply automated fixes"], cwd=tmpdir)
        run(["git", "push", "--set-upstream", "origin", "bot/sonar-fixes"], cwd=tmpdir)
        json.dump(fixed_keys, fixed_keys_path)

        pr_body = "This PR fixes the following SonarQube issues:\n\n" + "\n".join(pr_summary)
        pr_number = create_pr(repo, "bot/sonar-fixes", "fix(sonar): automated fixes", pr_body)
        print(f"🚀 Opened PR #{pr_number} with {len(targets)} fixes.")

if __name__ == "__main__":
    main()
