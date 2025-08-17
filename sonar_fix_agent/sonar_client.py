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

# Filter safe fixable Java rules
SAFE_RULES = {
    "java:S1128",  # unused imports
    "java:S1068",  # unused private fields
    "java:S1854",  # unused assignments
    "java:S1481",  # unused local variables
}

def choose_auto_fixables(issues):
    return [i for i in issues if i["rule"] in SAFE_RULES]
