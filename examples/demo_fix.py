"""
Demo of using HybridSonarFixer to fix SonarQube issues.
"""
import os
import sys
from pathlib import Path

# Add the parent directory to path so we can import the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from sonar_fix_agent.hybrid_sonar_fixer import HybridSonarFixer, SonarIssue

def main():
    # Initialize the fixer with project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fixer = HybridSonarFixer(
        project_root=project_root,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    
    # Create a sample SonarQube issue
    demo_file = os.path.join(project_root, 'examples', 'demo.java')
    issue = SonarIssue(
        rule="java:S1068",  # Unused import
        message="Remove this unused import 'java.util.List'.",
        file_path=demo_file,
        line=3
    )
    
    # Try to fix the issue
    results = fixer.fix_issues([issue])
    
    # Print results
    print("\n=== Fix Results ===")
    for result in results.get("fixed", []):
        print(f"✅ Fixed {result.get('rule')} at {result.get('file')}:{result.get('line')}")
        print(f"   Fix: {result.get('fix', 'No fix details')}")
    
    for result in results.get("failed", []):
        print(f"❌ Failed to fix {result.get('rule')} at {result.get('file')}:{result.get('line')}")
        print(f"   Reason: {result.get('reason', 'Unknown')}")

if __name__ == "__main__":
    main()
