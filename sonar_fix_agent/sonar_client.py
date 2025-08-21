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

# Expand safe rules to cover your target repo issues
SAFE_RULES = {
    "java:S1128",  # unused imports
    "java:S1068",  # unused private fields
    "java:S1854",  # unused assignments
    "java:S1481",  # unused local variables
    "java:S1118",  # add private constructor
    "java:UnusedLocalVariable",  # remove dbPassword
    "java:S125"   # remove commented-out code
}

def choose_auto_fixables(issues):
    # Only select issues that match SAFE_RULES
    selected = [i for i in issues if i["rule"] in SAFE_RULES]
    print(f"Found {len(selected)} auto-fixable issues")
    return selected
