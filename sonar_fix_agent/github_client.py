from github import Github, GithubException
from typing import Optional, Dict, Any

def get_github_repo(token: str, repo_full_name: str):
    """Initialize GitHub client and get repository."""
    try:
        g = Github(token)
        repo = g.get_repo(repo_full_name)
        print(f"✓ Connected to GitHub repository: {repo_full_name}")
        return repo
    except GithubException as e:
        print(f"❌ Failed to connect to GitHub repository {repo_full_name}: {str(e)}")
        raise

def create_pr(repo, branch: str, title: str, body: str, base: str = "main") -> Optional[int]:
    """
    Create a pull request with improved error handling and logging.
    
    Args:
        repo: GitHub repository object
        branch: Source branch name
        title: PR title
        body: PR description
        base: Target branch (default: main)
        
    Returns:
        PR number if successful, None otherwise
    """
    try:
        print(f"🔍 Checking for existing PRs for branch: {branch}")
        # Check for existing PRs for this branch
        existing_prs = repo.get_pulls(state="open", head=f"{repo.owner.login}:{branch}")
        
        if existing_prs.totalCount > 0:
            pr_number = existing_prs[0].number
            pr_url = existing_prs[0].html_url
            print(f"ℹ️ PR #{pr_number} already exists for branch '{branch}': {pr_url}")
            return pr_number

        print(f"📝 Creating new PR from {branch} to {base}")
        print(f"   Title: {title}")
        print(f"   Body length: {len(body)} characters")
        
        # Create new PR
        pr = repo.create_pull(
            title=title,
            body=body,
            head=branch,
            base=base,
            maintainer_can_modify=True
        )
        
        print(f"✅ Successfully created PR #{pr.number}")
        print(f"   URL: {pr.html_url}")
        print(f"   Title: {title}")
        print(f"   Branch: {branch} → {base}")
        
        return pr.number
        
    except Exception as e:
        print(f"❌ Failed to create PR: {str(e)}")
        if hasattr(e, 'data') and 'errors' in e.data:
            for error in e.data['errors']:
                print(f"   Error: {error.get('message', 'Unknown error')}")
        return None
    except GithubException as e:
        error_msg = str(e).lower()
        if "no commits between" in error_msg:
            print("ℹ️ No changes to commit. No PR created.")
        elif "A pull request already exists" in error_msg:
            print("ℹ️ A PR already exists for these changes.")
        else:
            print(f"❌ Failed to create PR: {str(e)}")
        return None
