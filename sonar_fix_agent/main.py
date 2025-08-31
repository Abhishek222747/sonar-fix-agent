import os
import tempfile
import random
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .config import MY_GITHUB_TOKEN, OPENAI_API_KEY, MAX_FIXES_PER_PR, SONAR_TOKEN, SONAR_URL
from .sonar_client import fetch_issues, choose_auto_fixables, list_projects
from .github_client import get_github_repo, create_pr
from .llm_fixer import generate_patch
from .java_sonar_fixer import JavaSonarFixer, SonarIssue
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
    
    # Get the project key from environment
    project_key = os.getenv("SONAR_PROJECT_KEY")
    if not project_key:
        print("❌ SONAR_PROJECT_KEY environment variable not set")
        print("Please set SONAR_PROJECT_KEY to one of these values:")
        projects = list_projects()
        if projects:
            for proj in projects:
                print(f"   - {proj.get('key')} (Name: {proj.get('name', 'N/A')})")
        return
    
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
        # Use the project key from environment variables
        if not project_key:
            print("❌ SONAR_PROJECT_KEY environment variable not set")
            return
            
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

            def process_sonar_issues(issues: List[Dict[str, Any]], tmpdir: str) -> List[Dict[str, Any]]:
                """Process Sonar issues and apply fixes."""
                fixed_issues = []
                java_fixer = JavaSonarFixer(tmpdir)
                
                # Group issues by file for more efficient processing
                issues_by_file = {}
                for issue in issues:
                    file_path = os.path.join(tmpdir, issue['component'].split(':')[-1])
                    if file_path not in issues_by_file:
                        issues_by_file[file_path] = []
                    issues_by_file[file_path].append(issue)
                
                # Process each file
                for file_path, file_issues in issues_by_file.items():
                    if not os.path.exists(file_path):
                        print(f"⚠️  File not found: {file_path}")
                        continue
                            
                    # Try to fix Java files with the AST-based fixer
                    if file_path.endswith('.java'):
                        for issue in file_issues:
                            sonar_issue = SonarIssue(
                                rule=issue['rule'],
                                message=issue['message'],
                                file_path=file_path,
                                line=issue.get('line', 0),
                                start_column=issue.get('start_column', 0),
                                end_column=issue.get('end_column', 0)
                            )
                            
                            try:
                                if java_fixer.fix_issue(sonar_issue):
                                    fixed_issues.append(issue)
                                    print(f"✅ [AST] Fixed {issue['rule']} in {os.path.basename(file_path)}")
                                else:
                                    print(f"⚠️  [AST] Could not fix {issue['rule']} in {os.path.basename(file_path)}")
                            except Exception as e:
                                print(f"❌ Error fixing {issue['rule']} in {os.path.basename(file_path)}: {str(e)}")
                    
                    # Fall back to LLM fixer for non-Java files or if AST fixer fails
                    for issue in file_issues:
                        if issue not in fixed_issues:  # Skip already fixed issues
                            with open(file_path, 'r', encoding='utf-8') as f:
                                original_code = f.read()
                            
                            fixed_code = generate_patch(file_path, original_code, issue['rule'], issue['message'])
                            
                            if fixed_code and fixed_code != original_code:
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    f.write(fixed_code)
                                fixed_issues.append(issue)
                                print(f"✅ [LLM] Fixed {issue['rule']} in {os.path.basename(file_path)}")
                            else:
                                print(f"⚠️  [LLM] Could not fix {issue['rule']} in {os.path.basename(file_path)}")
                
                return fixed_issues

            # Process issues and collect results
            fixed_issues = process_sonar_issues(targets, tmpdir)
            changed_files = set()
            fix_summary = []
            
            for issue in fixed_issues:
                file_path = os.path.join(tmpdir, issue['component'].split(':')[-1])
                changed_files.add(file_path)
                file_name = os.path.basename(file_path)
                fix_summary.append(f"- Fixed {issue['rule']}: {issue['message']} in `{file_name}`")
                print(f"✅ Fix applied to {file_name}")

            # If we made changes, commit and create PR
            if changed_files:
                print(f"\n💾 Found {len(changed_files)} files with changes")
                print("📝 Preparing to commit changes...")
                
                # Stage all changes
                run(["git", "status"], cwd=tmpdir)  # Debug: Show git status
                run(["git", "add", "."], cwd=tmpdir)
                
                # Create meaningful commit message
                commit_message = f"fix(sonar): Fix {len(targets)} Sonar issues\n\n"
                commit_message += "\n".join(f"- {issue['rule']}: {issue['message']}" for issue in targets[:5])
                if len(targets) > 5:
                    commit_message += f"\n- ... and {len(targets) - 5} more issues"
                
                # Commit changes
                commit_result = run(["git", "commit", "-m", commit_message], cwd=tmpdir)
                print(f"🔍 Commit result: {commit_result}")
                
                # Get current branch name
                branch_name = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=tmpdir).strip()
                print(f"🌿 Current branch: {branch_name}")
                
                # Push changes
                print("🚀 Pushing changes to GitHub...")
                push_result = run(["git", "push", "--set-upstream", "origin", branch_name], cwd=tmpdir)
                print(f"🔍 Push result: {push_result}")
                
                # Create PR
                print("📝 Creating pull request...")
                pr_title = f"fix(sonar): Fix {len(targets)} Sonar issues"
                
                pr_body = "## 🛠️ Automated SonarQube Fixes\n\n"
                pr_body += "This PR was automatically generated to fix the following SonarQube issues:\n\n"
                pr_body += "\n".join(f"- ✅ {issue['rule']}: {issue['message']}" for issue in targets[:10])
                if len(targets) > 10:
                    pr_body += f"\n- ... and {len(targets) - 10} more issues"
                
                pr_body += "\n\n---\n"
                pr_body += "*Automatically generated by [Sonar Fix Agent](https://github.com/Abhishek222747/sonar-fix-agent)*"
                
                # Get the default branch
                try:
                    default_branch = repo.default_branch
                    print(f"🌿 Default branch: {default_branch}")
                except Exception as e:
                    print(f"⚠️ Could not determine default branch, using 'main': {str(e)}")
                    default_branch = "main"
                
                # Create PR
                print(f"🚀 Creating PR from {branch_name} to {default_branch}")
                pr_number = create_pr(repo, branch_name, pr_title, pr_body, base=default_branch)
                
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
