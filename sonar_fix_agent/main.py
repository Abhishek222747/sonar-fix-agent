import os
import tempfile
import random
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .config import MY_GITHUB_TOKEN, OPENAI_API_KEY, MAX_FIXES_PER_PR, SONAR_TOKEN, SONAR_URL
from .sonar_client import fetch_issues, choose_auto_fixables, list_projects
from .github_client import get_github_repo, create_pr
from .llm_fixer import generate_patch
from .validator import run, validate_repo

def setup_git_repo(tmpdir: str, repo_full: str) -> bool:
    """Set up git repository with proper configuration."""
    try:
        # Configure git user
        run(["git", "config", "--global", "user.name", "Sonar Fix Bot"])
        run(["git", "config", "--global", "user.email", "sonar-fix-bot@users.noreply.github.com"])
        
        # Clone the repository
        clone_url = f"https://x-access-token:{MY_GITHUB_TOKEN}@github.com/{repo_full}.git"
        print(f"🔍 Cloning repository: {repo_full}")
        run(["git", "clone", "--depth", "1", clone_url, tmpdir])
        
        # Configure git in the cloned repo
        run(["git", "config", "user.name", "Sonar Fix Bot"], cwd=tmpdir)
        run(["git", "config", "user.email", "sonar-fix-bot@users.noreply.github.com"], cwd=tmpdir)
        
        # Create and switch to a new branch
        branch_name = f"bot/sonar-fixes-{int(time.time())}"
        run(["git", "checkout", "-b", branch_name], cwd=tmpdir)
        
        return True
    except Exception as e:
        print(f"❌ Failed to set up git repository: {str(e)}")
        return False

def main():
    print("🚀 Starting Sonar Fix Agent...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    # First, list all accessible projects to help with debugging
    list_projects()
    
    # Get the target repository from environment
    repo_full = os.getenv("REPOSITORY")
    if not repo_full:
        print("❌ Error: REPOSITORY environment variable not set")
        print("Please set the REPOSITORY environment variable (e.g., 'owner/repo')")
        return
        
    print(f"\n🔗 Target repository: {repo_full}")
    print(f"🔗 SonarQube URL: {SONAR_URL}")
    
    # Get the project key - try to use the same as the repo name if not set
    project_key = os.getenv("SONAR_PROJECT_KEY", repo_full.replace("/", ":"))
    print(f"🔑 Using project key: {project_key}")
    
    # Validate required environment variables
    if not all([MY_GITHUB_TOKEN, SONAR_TOKEN, SONAR_URL, OPENAI_API_KEY]):
        print("❌ Missing required environment variables. Please check:")
        print(f"   - GITHUB_TOKEN: {'✅' if MY_GITHUB_TOKEN else '❌'}")
        print(f"   - SONAR_TOKEN: {'✅' if SONAR_TOKEN else '❌'}")
        print(f"   - SONAR_URL: {'✅' if SONAR_URL else '❌'}")
        print(f"   - OPENAI_API_KEY: {'✅' if OPENAI_API_KEY else '❌'}")
        return

    # Get target repository
    repo_full = os.getenv("REPOSITORY")
    if not repo_full:
        print("❌ REPOSITORY environment variable is not set")
        print("   Please set it in the format: owner/repo")
        return

    print(f"🔗 Target repository: {repo_full}")
    print(f"🔗 SonarQube URL: {SONAR_URL}")
    print("-" * 50)

    # Initialize GitHub client
    try:
        print("🔌 Connecting to GitHub...")
        repo = get_github_repo(MY_GITHUB_TOKEN, repo_full)
        print(f"✅ Connected to GitHub repository: {repo.full_name}")
    except Exception as e:
        print(f"❌ Failed to connect to GitHub repository: {str(e)}")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"📂 Created temporary directory: {tmpdir}")
        
        # Set up git repository
        if not setup_git_repo(tmpdir, repo_full):
            return
            
        print("✅ Repository setup complete")
        print("-" * 50)

        # Fetch SonarQube issues
        print("🔍 Fetching SonarQube issues...")
        project_key = f"{repo_full.replace('/', ':')}"
        print(f"   Project key: {project_key}")
        
        try:
            issues = fetch_issues(project_key)
            print(f"✅ Found {len(issues)} total issues in SonarQube")
            
            # Filter auto-fixable issues
            targets = choose_auto_fixables(issues)
            print(f"🔧 Found {len(targets)} auto-fixable issues")
            
            if not targets:
                print("ℹ️ No auto-fixable issues found. No changes to make.")
                return

            # If too many issues, limit to MAX_FIXES_PER_PR
            if len(targets) > MAX_FIXES_PER_PR:
                print(f"⚠️  Found {len(targets)} fixable issues, limiting to {MAX_FIXES_PER_PR}")
                targets = random.sample(targets, MAX_FIXES_PER_PR)

            # Print the list of issues we're going to fix
            print("\n🔧 Issues to fix:")
            for i, issue in enumerate(targets, 1):
                print(f"   {i}. {issue['rule']}: {issue['message']} in {issue['component'].split(':')[-1]}")

            # Process each issue and apply fixes
            changed_files = set()
            fix_summary = []
            
            for issue in targets:
                try:
                    # Get file path from Sonar issue component
                    file_path = Path(tmpdir) / "/".join(issue["component"].split(":")[1:])
                    if not file_path.exists():
                        print(f"⚠️  File not found: {file_path}")
                        continue

                    print(f"\n🛠️  Processing: {file_path.name}")
                    print(f"   Rule: {issue['rule']}")
                    print(f"   Message: {issue['message']}")

                    # Read file content
                    code = file_path.read_text(encoding="utf-8", errors="ignore")
                    
                    # Generate patch
                    patch = generate_patch(str(file_path), code, issue["rule"], issue["message"])
                    if not patch:
                        print("   ℹ️  No fix needed or could not generate patch")
                        continue

                    # Apply patch by writing the complete file
                    file_path.write_text(patch, encoding="utf-8")
                    changed_files.add(file_path)
                    
                    # Add to fix summary
                    fix_summary.append(f"- Fixed {issue['rule']}: {issue['message']} in `{file_path.name}`")
                    print("   ✅ Fix applied")

                except Exception as e:
                    print(f"❌ Error processing {file_path.name}: {str(e)}")
                    continue

            # If we made changes, commit and create PR
            if changed_files:
                print("\n💾 Committing changes...")
                run(["git", "add", "-A"], cwd=tmpdir)
                
                # Create meaningful commit message
                commit_message = f"fix(sonar): Fix {len(changed_files)} Sonar issues\n\n"
                commit_message += "\n".join(f"- {issue['rule']}: {issue['message']}" for issue in targets[:5])
                if len(targets) > 5:
                    commit_message += f"\n- ... and {len(targets) - 5} more issues"
                
                run(["git", "commit", "-m", commit_message], cwd=tmpdir)
                
                # Push changes
                print("🚀 Pushing changes to GitHub...")
                run(["git", "push", "--set-upstream", "origin", f"HEAD"], cwd=tmpdir)
                
                # Create PR
                print("📝 Creating pull request...")
                pr_title = f"fix(sonar): Fix {len(changed_files)} Sonar issues"
                
                pr_body = "## Automated SonarQube Fixes\n\n"
                pr_body += "This PR was automatically generated to fix the following SonarQube issues:\n\n"
                pr_body += "\n".join(fix_summary)
                pr_body += "\n\n---\n"
                pr_body += "*Auto-generated by Sonar Fix Agent*"
                
                # Get current branch name
                branch_name = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=tmpdir, capture_output=True, text=True).stdout.strip()
                
                pr_number = create_pr(
                    repo=repo,
                    branch=branch_name,
                    title=pr_title,
                    body=pr_body,
                    base="main"
                )
                
                if pr_number:
                    print(f"✅ Successfully created PR #{pr_number}")
                else:
                    print("⚠️  Failed to create PR")
            else:
                print("\nℹ️  No changes were made. All issues are either already fixed or couldn't be automatically resolved.")
                    
        except Exception as e:
            print(f"❌ Error in main execution: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
