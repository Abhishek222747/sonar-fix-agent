import requests
from .config import SONAR_TOKEN, SONAR_URL

def fetch_issues(project_key):
    url = f"{SONAR_URL}/api/issues/search"
    params = {
        "componentKeys": project_key,
        "severities": "MAJOR,CRITICAL,BLOCKER",
        "ps": 500
    }
    response = requests.get(url, params=params, auth=(SONAR_TOKEN, ''))
    response.raise_for_status()
    return response.json().get("issues", [])

# Exact rules for the 3 current issues in your target repo
SAFE_RULES = {
    "java:S1118",            # Add private constructor
    "java:UnusedLocalVariable",  # Remove unused local variable "dbPassword"
    "java:S125"              # Remove commented-out lines
}

def choose_auto_fixables(issues):
    selected = [i for i in issues if i["rule"] in SAFE_RULES]
    print(f"Found {len(selected)} auto-fixable issues")
    for i in selected:
        print(f"- {i['component']} : {i['message']} ({i['rule']})")
    return selected
