import os
import tempfile
from pathlib import Path
from .config import GITHUB_TOKEN, MAX_FIXES_PER_PR, SONAR_TOKEN, SONAR_URL
from .sonar_client import fetch_issues, choose_auto_fixables
from .github_client import get_github_repo, create_pr
from .llm_fixer import generate_patch
from .validator import run

def main():
    repo_full = os.getenv("GITHUB_REPOSITORY")
    if not repo_full:
        print("Set GITHUB_REPOSITORY env var (e.g., user/repo)")
        return

    repo = get_github_repo(GITHUB_TOKEN, repo_full)

    with tempfile.TemporaryDirectory() as tmpdir:
        clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{repo_full}.git"
        print(f"Cloning repo {repo_full} into {tmpdir}")
        run(["git", "clone", clone_url, tmpdir])
        run(["git", "config", "user.name", "github-actions[bot]"], cwd=tmpdir)
        run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], cwd=tmpdir)
        run(["git", "checkout", "-b", "bot/sonar-fixes"], cwd=tmpdir)

        project_key = repo_full.replace("/", ":")
        issues = fetch_issues(project_key)
        print(f"All issues fetched from SonarCloud ({len(issues)}): {[i['rule'] for i in issues]}")

        targets = choose_auto_fixables(issues, max_fixes=MAX_FIXES_PER_PR)
        print(f"Selected issues for fix: {[i['rule'] for i in targets]}")

        if not targets:
            print("No issues selected to fix.")
            return

        changed_files = set()
        for issue in targets:
            file_path = Path(tmpdir) / "/".join(issue["component"].split(":")[1:])
            if not file_path.exists():
                print(f"File not found for issue: {file_path}")
                continue

            code = file_path.read_text(encoding="utf-8", errors="ignore")
            patch = generate_patch(str(file_path), code, issue["rule"], issue["message"])
            if not patch:
                print(f"No patch generated for {file_path}")
                continue

            patch_file = Path(tmpdir) / ".tmp.patch"
            patch_file.write_text(patch)

            try:
                run(["git", "apply", "--whitespace=fix", str(patch_file)], cwd=tmpdir)
                changed_files.add(file_path)
            except Exception as e:
                print(f"Failed to apply patch for {file_path}: {e}")
                run(["git", "checkout", "--", str(file_path)], cwd=tmpdir)
                continue

        if not changed_files:
            print("No fixes applied, but PR can still be created for tracking.")
            # Optional: create empty commit to raise PR
            run(["git", "commit", "--allow-empty", "-m", "Track Sonar issues PR"], cwd=tmpdir)

        else:
            run(["git", "add", "-A"], cwd=tmpdir)
            run(["git", "commit", "-m", f"fix(sonar): applied {len(changed_files)} automated fixes"], cwd=tmpdir)

        run(["git", "push", "--set-upstream", "origin", "bot/sonar-fixes"], cwd=tmpdir)

        pr_number = create_pr(
            repo,
            "bot/sonar-fixes",
            "fix(sonar): automated fixes",
            f"This PR attempts to fix {len(changed_files)} Sonar issues automatically."
        )
        print(f"Opened PR #{pr_number}")


if __name__ == "__main__":
    main()
