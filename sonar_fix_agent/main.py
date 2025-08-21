import os
import tempfile
from pathlib import Path
from .config import GITHUB_TOKEN, OPENAI_API_KEY, MAX_FIXES_PER_PR
from .sonar_client import fetch_issues, choose_auto_fixables
from .github_client import get_github_repo, create_pr
from .llm_fixer import generate_patch
from .validator import run, validate_repo

def main():
    repo_full = os.getenv("GITHUB_REPOSITORY")
    if not repo_full:
        print("Set GITHUB_REPOSITORY env var (e.g., user/repo)")
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
        targets = choose_auto_fixables(issues)

        if not targets:
            print("No auto-fixable issues found.")
            return

        # Limit fixes per PR
        targets = targets[:MAX_FIXES_PER_PR]
        changed_files = set()

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
            except Exception as e:
                print(f"Failed to apply patch for {file_path}: {e}")
                run(["git", "checkout", "--", str(file_path)], cwd=tmpdir)
                continue

        if not changed_files:
            print("No fixes applied.")
            return

        run(["git", "add", "-A"], cwd=tmpdir)
        run(["git", "commit", "-m", f"fix(sonar): applied {len(changed_files)} automated fixes"], cwd=tmpdir)
        run(["git", "push", "--set-upstream", "origin", "bot/sonar-fixes"], cwd=tmpdir)

        pr_number = create_pr(
            repo,
            "bot/sonar-fixes",
            "fix(sonar): automated fixes",
            f"This PR fixes {len(changed_files)} Sonar issues automatically."
        )
        print(f"Opened PR #{pr_number}")

if __name__ == "__main__":
    main()
