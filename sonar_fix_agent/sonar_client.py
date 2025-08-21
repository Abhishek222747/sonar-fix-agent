import os
import requests
import random

SONAR_TOKEN = os.getenv("SONAR_TOKEN")
SONAR_URL = os.getenv("SONAR_URL")  # e.g., https://sonarcloud.io

def fetch_issues(project_key):
    """
    Fetch all issues from SonarCloud for the given project_key.
    Returns a list of issue dicts.
    """
    issues = []
    page = 1
    page_size = 500

    while True:
        url = f"{SONAR_URL}/api/issues/search"
        params = {
            "componentKeys": project_key,
            "ps": page_size,
            "p": page,
            "resolved": "false",
        }
        response = requests.get(url, params=params, auth=(SONAR_TOKEN, ""))
        response.raise_for_status()
        data = response.json()
        page_issues = data.get("issues", [])
        if not page_issues:
            break
        issues.extend(page_issues)
        if len(page_issues) < page_size:
            break
        page += 1

    return issues

def choose_auto_fixables(issues, max_fixes=3):
    """
    Randomly selects up to max_fixes issues to attempt fixing.
    """
    if not issues:
        return []
    return random.sample(issues, min(len(issues), max_fixes))
