import requests
from .config import SONAR_TOKEN, SONAR_URL

def fetch_issues(project_key):
    """
    Fetch all issues from SonarCloud for the given project_key.
    Handles pagination automatically.
    """
    issues = []
    page = 1
    page_size = 100  # Reduced page size for better reliability
    
    print(f"🔍 Fetching issues for project: {project_key}")
    print(f"🔗 SonarQube URL: {SONAR_URL}")
    print(f"🔑 Using token: {'*' * 8}{SONAR_TOKEN[-4:] if SONAR_TOKEN else 'None'}")

    while True:
        url = f"{SONAR_URL.rstrip('/')}/api/issues/search"
        params = {
            "componentKeys": project_key,
            "resolved": "false",
            "ps": page_size,
            "p": page,
            "statuses": "OPEN,CONFIRMED,REOPENED"  # Explicitly request open issues
        }

        print(f"\n📡 Requesting page {page}...")
        print(f"   URL: {url}")
        print(f"   Params: { {k: v for k, v in params.items() if k != 'ps' and k != 'p'} }")

        try:
            # Basic auth using SONAR_TOKEN
            response = requests.get(
                url, 
                params=params, 
                auth=(SONAR_TOKEN, ""),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # Debug: Print API response keys
            print(f"   Response keys: {list(data.keys())}")
            
            if "issues" in data:
                page_issues = data["issues"]
                issues.extend(page_issues)
                print(f"   ✅ Fetched {len(page_issues)} issues from page {page}")
                
                # Debug: Print first few issues if any
                if page_issues and page == 1:
                    print("\n📝 Sample issue:")
                    sample = page_issues[0]
                    print(f"   Rule: {sample.get('rule')}")
                    print(f"   Message: {sample.get('message')}")
                    print(f"   Component: {sample.get('component')}")
            else:
                print(f"   ⚠️ No 'issues' key in response. Available keys: {list(data.keys())}")
                if "errors" in data:
                    print(f"   ❌ Errors: {data['errors']}")
                break

            # Check if there are more pages
            total = data.get("total", 0)
            print(f"   Total issues in SonarQube: {total}")
            
            if len(issues) >= total or not page_issues:
                break
                
            page += 1
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error fetching page {page}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response status: {e.response.status_code}")
                print(f"   Response body: {e.response.text}")
            break

    print(f"\n📊 Total issues fetched: {len(issues)}")
    if issues:
        print(f"   First issue rule: {issues[0].get('rule')}")
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
