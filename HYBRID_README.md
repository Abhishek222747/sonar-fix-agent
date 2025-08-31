# Hybrid Sonar Fix Agent

A hybrid approach to fixing SonarQube issues in Java code, combining:
- **AST Analysis**: For precise, rule-based code transformations
- **Semantic Analysis**: For understanding code context and relationships
- **LLM (Large Language Models)**: For complex refactoring and pattern matching

## Features

- **AST-based Fixes**: Fast, reliable fixes for common issues
- **Semantic Analysis**: Understands code context and relationships
- **LLM Integration**: Handles complex refactoring with AI assistance
- **Incremental Analysis**: Only analyzes what's needed
- **Cross-file Awareness**: Understands dependencies between files

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/sonar-fix-agent.git
   cd sonar-fix-agent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your OpenAI API key (optional, for LLM features):
   ```bash
   # On Linux/macOS
   echo "export OPENAI_API_KEY='your-api-key'" >> ~/.bashrc
   source ~/.bashrc

   # On Windows
   setx OPENAI_API_KEY "your-api-key"
   ```

## Usage

### Basic Usage

```python
from sonar_fix_agent.hybrid_sonar_fixer import HybridSonarFixer, SonarIssue

# Initialize the fixer
fixer = HybridSonarFixer(
    project_root="/path/to/your/project",
    openai_api_key="your-api-key"  # Optional
)

# Define issues to fix
issues = [
    SonarIssue(
        rule="java:S1068",
        message="Remove this unused import 'java.util.List'.",
        file_path="src/main/java/com/example/Demo.java",
        line=3
    )
]

# Fix the issues
results = fixer.fix_issues(issues)
print(results)
```

### Example: Fixing Common Issues

```python
# Example of fixing multiple issue types
issues = [
    # Unused import
    SonarIssue("java:S1068", "Unused import", "Demo.java", 3),
    # Boolean literal comparison
    SonarIssue("java:S1125", "Boolean literal comparison", "Demo.java", 8),
    # Commented-out code
    SonarIssue("java:S125", "Commented out code", "Demo.java", 12),
    # Unused local variable
    SonarIssue("java:S1481", "Unused local variable", "Demo.java", 15),
    # Cognitive complexity
    SonarIssue("java:S3776", "Refactor this method to reduce complexity", "Demo.java", 20)
]

results = fixer.fix_issues(issues)
```

## How It Works

1. **AST-based Fixes**:
   - Parses Java code into an Abstract Syntax Tree (AST)
   - Applies rule-based transformations
   - Handles simple cases like unused imports, boolean comparisons, etc.

2. **Semantic Analysis**:
   - Builds a symbol table
   - Tracks variable usage and types
   - Understands method calls and class relationships

3. **LLM Integration**:
   - Used when AST and semantic analysis aren't sufficient
   - Provides context-aware code generation
   - Handles complex refactoring tasks

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required for LLM features)
- `SONAR_HOST_URL`: SonarQube server URL (if using Sonar integration)
- `SONAR_TOKEN`: SonarQube authentication token

### Custom Fixers

You can extend the `HybridSonarFixer` class to add custom fixers:

```python
class CustomSonarFixer(HybridSonarFixer):
    def _try_ast_fix(self, issue, ast_analyzer):
        # Add custom AST-based fixers here
        if issue.rule == "custom:my-rule":
            return self._fix_my_custom_rule(issue, ast_analyzer)
        return super()._try_ast_fix(issue, ast_analyzer)
```

## Testing

Run the demo to see the fixer in action:

```bash
python examples/demo_fix.py
```

## Limitations

- Currently focuses on Java code
- LLM features require an OpenAI API key
- Some complex refactorings may require manual review

## License

MIT
