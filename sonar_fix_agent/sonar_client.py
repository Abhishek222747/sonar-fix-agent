import requests
from .config import SONAR_TOKEN, SONAR_URL

def fetch_issues(project_key):
    """
    Fetch all issues for the given project key from SonarCloud.
    Returns a list of issue dicts.
    """
    url = f"{SONAR_URL}/api/issues/search"
    params = {
        "componentKeys": project_key,
        "ps": 500  # maximum number of issues per request
    }

    try:
        response = requests.get(url, params=params, auth=(SONAR_TOKEN, ''))
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching issues from SonarCloud: {e}")
        return []

    data = response.json()
    issues = data.get("issues", [])

    print(f"Found {len(issues)} issues in SonarCloud for project {project_key}.")
    for i, issue in enumerate(issues, 1):
        print(f"{i}. {issue.get('rule')} - {issue.get('message')} (severity: {issue.get('severity')})")
    return issues

# Include rules that are safe to auto-fix
SAFE_RULES = {
    # your specific issues in target repo
    "java:S1118",              # Add private constructor
    "java:UnusedLocalVariable", # Remove unused local variable
    "java:S125",               # Remove commented-out lines
    "java:S1068",              # unused private fields
    "java:S1128",              # unused imports
    "java:S1854",              # unused assignments
    "java:S1481",              # unused local variables
}

def choose_auto_fixables(issues):
    """
    Filter only issues whose rules are in SAFE_RULES
    """
    auto_fixables = [i for i in issues if i.get("rule") in SAFE_RULES]
    print(f"Auto-fixable targets: {len(auto_fixables)}")
    return auto_fixables
