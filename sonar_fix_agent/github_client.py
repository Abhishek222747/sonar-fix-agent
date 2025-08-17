from github import Github

def get_github_repo(token, repo_full_name):
    g = Github(token)
    return g.get_repo(repo_full_name)

def create_pr(repo, branch, title, body):
    pr = repo.create_pull(title=title, body=body, head=branch, base="main")
    return pr.number
