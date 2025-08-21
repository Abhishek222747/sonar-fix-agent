import requests
from .config import SONAR_TOKEN, SONAR_URL

def fetch_issues(project_key, severities=None):
    """
    Fetch all issues for the given project key from SonarQube.
    By default, fetch all severities.
    """
    url = f"{SONAR_URL}/api/issues/search"
    params = {
        "componentKeys": project_key,
        "ps": 500  # page size
    }
    if severities:
        params["severities"] = ",".join(severities)

    response = requests.get(url, params=params, auth=(SONAR_TOKEN, ''))
    response.raise_for_status()
    return response.json().get("issues", [])
