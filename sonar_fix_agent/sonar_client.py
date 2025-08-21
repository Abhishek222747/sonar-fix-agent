import requests
from .config import SONAR_TOKEN, SONAR_URL

def fetch_issues(project_key):
    """
    Fetch all issues from SonarCloud for the given project_key.
    Handles pagination automatically.
    """
    issues = []
    page = 1
    page_size = 500  # SonarCloud max per page

    while True:
        url = f"{SONAR_URL}/api/issues/search"
        params = {
            "componentKeys": project_key,
            "resolved": "false",
            "ps": page_size,
            "p": page
        }

        # Basic auth using SONAR_TOKEN
        response = requests.get(url, params=params, auth=(SONAR_TOKEN, ""))
        response.raise_for_status()
        data = response.json()

        if "issues" in data:
            issues.extend(data["issues"])
            print(f"Fetched {len(data['issues'])} issues from page {page}")
        else:
            print(f"No 'issues' key in response for page {page}: {data}")
            break

        # Check if there are more pages
        total = data.get("total", 0)
        if len(issues) >= total:
            break

        page += 1

    print(f"Total issues fetched: {len(issues)}")
    return issues

def choose_auto_fixables(issues):
    """
    Filter issues that can be auto-fixed by the agent.
    Currently we consider some common safe rules.
    """
    SAFE_RULES = {
        "java:S1118",            # Add private constructor
        "java:UnusedLocalVariable",  # Remove unused local variable
        "java:S125"              # Remove commented-out lines
    }

    auto_fixable = [issue for issue in issues if issue.get("rule") in SAFE_RULES]
    return auto_fixable
