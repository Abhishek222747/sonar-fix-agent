import requests
from .config import SONAR_TOKEN, SONAR_URL

def fetch_issues(project_key):
    """
    Fetch all issues from SonarCloud for the given project_key.
    Handles pagination automatically.
    ""
    def try_fetch_issues(params, endpoint="issues/search"):
        """Helper function to try fetching issues with given parameters"""
        nonlocal page, page_size, issues
        
        while True:
            url = f"{SONAR_URL.rstrip('/')}/api/{endpoint}"
            params.update({"ps": page_size, "p": page})
            
            print(f"\n📡 Requesting {endpoint} (page {page})...")
            print(f"   URL: {url}")
            print(f"   Params: { {k: v for k, v in params.items() if k not in ['ps', 'p']} }")

            try:
                response = requests.get(
                    url, 
                    params=params, 
                    auth=(SONAR_TOKEN, "") if SONAR_TOKEN else None,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                print(f"   Response keys: {list(data.keys())}")
                
                # Handle different response formats
                if "issues" in data:
                    page_issues = data["issues"]
                    total = data.get("total", 0)
                    print(f"   ✅ Fetched {len(page_issues)} issues from page {page}")
                    print(f"   Total issues in response: {total}")
                    
                    if page_issues:
                        print("\n📝 Sample issue:")
                        sample = page_issues[0]
                        for key in ['rule', 'message', 'component', 'status', 'severity']:
                            print(f"   {key}: {sample.get(key)}")
                    
                    return page_issues, total
                
                elif "hotspots" in data:  # For security hotspots
                    page_issues = data["hotspots"]
                    total = data.get("paging", {}).get("total", 0)
                    print(f"   🔥 Fetched {len(page_issues)} security hotspots from page {page}")
                    return page_issues, total
                
                else:
                    print(f"   ⚠️ Unexpected response format. Available keys: {list(data.keys())}")
                    if "errors" in data:
                        print(f"   ❌ Errors: {data['errors']}")
                    return [], 0
                
            except requests.exceptions.RequestException as e:
                print(f"   ❌ Error: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"   Status: {e.response.status_code}")
                    print(f"   Body: {e.response.text[:500]}")
                return [], 0
    
    # Initialize variables
    issues = []
    page = 1
    page_size = 50  # Smaller page size for reliability
    
    print(f"🔍 Fetching issues for project: {project_key}")
    print(f"🔗 SonarQube URL: {SONAR_URL}")
    print(f"🔑 Using token: {'*' * 8}{SONAR_TOKEN[-4:] if SONAR_TOKEN else 'None'}")
    
    # Try different API endpoints and parameters
    endpoints_to_try = [
        # Try with component key as is
        ({"componentKeys": project_key, "resolved": "false"}, "issues/search"),
        # Try with project key only (without organization)
        ({"componentKeys": project_key.split(':')[-1], "resolved": "false"}, "issues/search"),
        # Try with additional parameters
        ({"componentKeys": project_key, "statuses": "OPEN,CONFIRMED,REOPENED"}, "issues/search"),
        # Try with all issues including resolved ones
        ({"componentKeys": project_key}, "issues/search"),
        # Try the project_issues endpoint
        ({"project": project_key}, "project_issues/search"),
        # Try hotspots endpoint
        ({"projectKey": project_key}, "hotspots/search"),
    ]
    
    for params, endpoint in endpoints_to_try:
        print(f"\n🔍 Trying endpoint: {endpoint} with params: {params}")
        page_issues, total = try_fetch_issues(params, endpoint)
        
        if page_issues:
            issues.extend(page_issues)
            print(f"✅ Successfully fetched {len(page_issues)} issues using {endpoint}")
            break
    
    # If still no issues, try to get project info to verify the project key
    if not issues:
        print("\n🔍 No issues found. Trying to verify project key...")
        try:
            url = f"{SONAR_URL.rstrip('/')}/api/components/show"
            response = requests.get(
                url,
                params={"component": project_key},
                auth=(SONAR_TOKEN, "") if SONAR_TOKEN else None,
                timeout=10
            )
            if response.status_code == 200:
                project_info = response.json()
                print(f"✅ Project found: {project_info.get('component', {}).get('name')}")
                print(f"   Key: {project_info.get('component', {}).get('key')}")
                print(f"   Qualifier: {project_info.get('component', {}).get('qualifier')}")
            else:
                print(f"⚠️ Project not found or not accessible (Status: {response.status_code})")
                print(f"   Response: {response.text[:500]}")
        except Exception as e:
            print(f"❌ Error verifying project: {str(e)}")
    
    print(f"\n📊 Total issues found: {len(issues)}")
    if issues:
        print(f"   First issue rule: {issues[0].get('rule', 'N/A')}")
    else:
        print("   No issues found. Please verify:")
        print("   1. The project key is correct")
        print("   2. The token has the right permissions")
        print("   3. There are actually issues in the project")
        print("   4. The issues are not filtered out by the query parameters")
    
    return issues

def choose_auto_fixables(issues):
    """
    Filter issues that can be auto-fixed by the agent.
    Currently we consider some common safe rules.
    """
    # Expanded list of auto-fixable rules
    SAFE_RULES = {
        # Java rules
        "java:S1118",    # Add a private constructor to hide the implicit public one
        "java:S1481",   # Remove unused local variables
        "java:S125",     # Remove commented-out code
        "java:S1068",    # Unused private fields should be removed
        "java:S1144",    # Unused "private" methods should be removed
        "java:S1134",    # "FIXME" tags should be handled
        "java:S1135",    # "TODO" tags should be handled
        "java:S1125",    # Boolean literals should not be redundant
        "java:S1121",    # Assignments should not be made from within sub-expressions
        "java:S1128",    # Unused imports should be removed
        "java:S1488",    # Local Variables should not be declared and then immediately returned or thrown
        "java:S1854",    # Unused assignments should be removed
        "java:S2094",    # Classes should not be empty
        "java:S2097",    # "@Nonnull" or similar annotations should not be used on methods with primitive return types
        "java:S2130",    # Parsing should be used to convert "Strings" to primitives
        "java:S2209",    # "@NonNull" values should not be set to null
        "java:S2786",    # "assertTrue" should not be used to test the Strings returned by "toString()"
        "java:S2975",    # "@Nonnull" or similar annotations should not be used on methods with primitive return types
        "java:S3457",    # "String#replace" should be preferred to "String#replaceAll"
        "java:S3862",    # "@Nonnull" or similar annotations should not be used on methods with primitive return types
        "java:S4275",    # "@Nonnull" or similar annotations should not be used on methods with primitive return types
        "java:S4973",    # "@Nonnull" or similar annotations should not be used on methods with primitive return types
        
        # Common code smells that can be auto-fixed
        "common-java:InsufficientCommentDensity",
        "common-java:InsufficientLineCoverage",
        "common-java:DuplicatedBlocks",
    }
    
    print(f"\n🔍 Analyzing {len(issues)} issues for auto-fixable patterns...")
    
    # Debug: Print all unique rule types
    rule_types = {issue.get('rule') for issue in issues}
    print(f"Found {len(rule_types)} unique rule types in SonarQube issues:")
    for i, rule in enumerate(sorted(rule_types), 1):
        print(f"  {i}. {rule}")
    
    # Filter issues by safe rules
    auto_fixable = []
    for issue in issues:
        rule = issue.get('rule')
        if rule in SAFE_RULES:
            auto_fixable.append(issue)
            print(f"✅ Will fix {rule}: {issue.get('message')}")
    
    print(f"\n📊 Found {len(auto_fixable)} auto-fixable issues out of {len(issues)} total issues")
    
    return auto_fixable
