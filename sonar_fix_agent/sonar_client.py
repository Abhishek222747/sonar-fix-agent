import requests
from .config import SONAR_TOKEN, SONAR_URL

def fetch_issues(project_key):
    """
    Fetch all issues from SonarCloud for a given project key.
    """
    url = f"{SONAR_URL}/api/issues/search"
    params = {
        "componentKeys": project_key,
        "severities": "MAJOR,CRITICAL,BLOCKER",
        "ps": 500  # max page size
    }
    response = requests.get(url, params=params, auth=(SONAR_TOKEN.strip(), ''))
    response.raise_for_status()
    return response.json().get("issues", [])

def choose_auto_fixables(issues, max_fixes=None):
    """
    Return issues that can be auto-fixed.
    Currently allows all issues for testing.
    """
    if max_fixes:
        return issues[:max_fixes]  # batch
    return issues
