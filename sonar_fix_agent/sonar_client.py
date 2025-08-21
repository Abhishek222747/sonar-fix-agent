import os
import requests
import random
from .config import SONAR_TOKEN, SONAR_URL

def fetch_issues(project_key: str):
    """
    Fetch all open issues from SonarCloud for the given project_key.
    Returns a list of issues.
    """
    issues = []
    page = 1
    page_size = 500  # SonarCloud maximum
    while True:
        url = f"{SONAR_URL}/api/issues/search"
        params = {
            "componentKeys": project_key,
            "resolved": "false",
            "ps": page_size,
            "p": page
        }
        response = requests.get(url, params=params, auth=(SONAR_TOKEN, ""))
        response.raise_for_status()
        data = response.json()
        issues.extend(data.get("issues", []))
        if page * page_size >= data.get("total", 0):
            break
        page += 1

    return issues

def choose_auto_fixables(issues):
    """
    Select only auto-fixable issues.
    If too many, pick up to 3 random issues.
    """
    SAFE_RULES = {
        "java:S1118",            # Add private constructor
        "java:UnusedLocalVariable",  # Remove unused local variable
        "java:S125"              # Remove commented-out lines
    }

    auto_fixable = [i for i in issues if i.get("rule") in SAFE_RULES]

    # pick 2–3 random if too many
    if len(auto_fixable) > 3:
        auto_fixable = random.sample(auto_fixable, 3)

    return auto_fixable
