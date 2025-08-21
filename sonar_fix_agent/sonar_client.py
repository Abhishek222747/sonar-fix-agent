import requests
from .config import SONAR_TOKEN, SONAR_URL

# Set of rules we want to auto-fix
SAFE_RULES = {
    "java:S1118",            # Add private constructor
    "java:UnusedLocalVariable",  # Remove unused local variable
    "java:S125"              # Remove commented-out lines
}

def fetch_issues(project_key):
    """
    Fetch all issues from SonarCloud for the given project key.
    """
    url = f"{SONAR_URL}/api/issues/search"
    params = {"componentKeys": project_key, "ps": 500}
    print(f"Fetching issues from SonarCloud: {url} for project {project_key}")
    response = requests.get(url, params=params, auth=(SONAR_TOKEN, ''))
    response.raise_for_status()
    issues = response.json().get("issues", [])
    print(f"Fetched {len(issues)} issues")
    return issues

def choose_auto_fixables(issues):
    """
    Return only issues that are safe to auto-fix according to SAFE_RULES
    """
    auto_fixables = [i for i in issues if i["rule"] in SAFE_RULES]
    return auto_fixables
