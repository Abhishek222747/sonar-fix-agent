import os
import tempfile
import random
from pathlib import Path
from .config import GITHUB_TOKEN, OPENAI_API_KEY, MAX_FIXES_PER_PR, SONAR_TOKEN, SONAR_URL
from .sonar_client import fetch_issues, choose_auto_fixables
from .github_client import get_github_repo, create_pr
from .llm_fixer import generate_patch
from .validator import run, validate_repo

def main():
    print("Starting Sonar Fix Agent...")

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

        # Delete old branch if exists to avoid push conflicts
        run(["git", "checkout", "main"], cwd=tmpdir)
        run(["git", "branch", "-D", "bot/sonar-fixes"], cwd=tmpdir, check=False)
        run(["git", "checkout", "-b", "bot/sonar-fixes"], cwd=tmpdir)

        # Fetch all Sonar issues
        project_key = repo_full.replace("/", ":")
        issues = fetch_issues(project_key)
        print(f"All issues fetched from SonarCloud: {len(issues)}")

        # Select auto-fixable issues
        targets = choose_auto_fixables(issues)

        # If too many issues, pick random 2–3
        if len(targets) > MAX_FIXES_PER_PR:
            targets = random.sample(targets, MAX_FIXES_PER_PR)

        print(f"Auto-fixable targets ({len(targets)}): {[i['rule'] for i in targets]}")
        if not targets:
            print("No auto-fixable issues found. Creating empty PR to test integration.")

        changed_files = set()
        for issue in targets:
            file_path = Path(tmpdir)/"/".join(issue["component"].split(":")[1:])
            if not file_path.exists():
                print(f"File not found for issue: {file_path}")
                continue

            code = file_path.read_text(encoding="utf-8", errors="ignore")
            patch = generate_patch(str(file_path), code, issue["rule"], issue["message"])
            if not patch:
                print(f"No patch generated for {file_path}")
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

        run(["git", "add", "-A"], cwd=tmpdir)

        if changed_files:
            run(["git", "commit", "-m", f"fix(sonar): applied {len(changed_files)} automated fixes"], cwd=tmpdir)
        else:
            # Empty commit to create PR even if no fixes applied
            run(["git", "commit", "--allow-empty", "-m", "Test PR: no fixes applied"], cwd=tmpdir)

        # Force push to avoid non-fast-forward errors
        run(["git", "push", "--set-upstream", "origin", "bot/sonar-fixes", "--force"], cwd=tmpdir)

        pr_number = create_pr(
            repo,
            "bot/sonar-fixes",
            "fix(sonar): automated fixes",
            f"This PR fixes {len(changed_files)} Sonar issues automatically."
        )
        print(f"Opened PR #{pr_number}")

if __name__ == "__main__":
    main()
