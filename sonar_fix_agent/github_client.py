from github import Github

def get_github_repo(token, repo_full_name):
    g = Github(token)
    return g.get_repo(repo_full_name)

def create_pr(repo, branch, title, body, base="main"):
    # Avoid duplicate PRs
    existing_prs = repo.get_pulls(state="open", head=f"{repo.owner.login}:{branch}")
    if existing_prs.totalCount > 0:
        print(f"⚠️ PR already exists for branch {branch}, returning existing PR number.")
        return existing_prs[0].number

    pr = repo.create_pull(title=title, body=body, head=branch, base=base)
    print(f"✅ Created PR #{pr.number} from branch {branch} to {base}")
    return pr.number
