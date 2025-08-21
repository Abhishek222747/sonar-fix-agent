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

# Exact rules for your 3 current issues
SAFE_RULES = {
    "java:S1118",   # Add a private constructor
    "java:S1481",   # Remove unused local variable "dbPassword"
    "java:S125"     # Remove commented-out lines
}

def choose_auto_fixables(issues):
    print("All issues fetched from SonarCloud:")
    for i in issues:
        print(f"{i['component']} → {i['rule']}: {i['message']}")
    return [i for i in issues if i["rule"] in SAFE_RULES]

