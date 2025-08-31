# Sonar Fix Agent with AST-based Java Fixes

This enhanced version of the Sonar Fix Agent now includes advanced AST (Abstract Syntax Tree) based analysis for fixing complex Java Sonar issues. The agent can now understand and modify Java code structure while maintaining semantic correctness.

## Key Features

1. **AST-based Java Analysis**
   - Full Java syntax parsing
   - Cross-file dependency tracking
   - Precise code modification capabilities

2. **Supported Java Sonar Issues**
   - `java:S1068`: Unused imports
   - `java:S1125`: Boolean literal comparison
   - `java:S3776`: Complex method refactoring
   - `java:S125`: Removal of commented-out code
   - `java:S1118`: Adding private constructors to utility classes

3. **Intelligent Fixing**
   - Context-aware code modifications
   - Cross-file impact analysis
   - Fallback to LLM-based fixing when AST fixing is not applicable

## How It Works

1. **AST Parsing**: The agent parses Java source code into an Abstract Syntax Tree (AST) using `javalang`.
2. **Dependency Analysis**: Builds a dependency graph of the codebase to understand cross-file relationships.
3. **Issue Detection**: Identifies fixable Sonar issues in the code.
4. **Targeted Fixing**: Applies appropriate fixes based on the issue type:
   - AST-based fixes for Java files
   - LLM-based fixes for other file types or complex cases
5. **Impact Analysis**: Verifies that changes won't break dependent code.

## Getting Started

### Prerequisites

- Python 3.8+
- Java Development Kit (JDK) 11+
- SonarQube server access
- GitHub repository access

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/sonar-fix-agent.git
   cd sonar-fix-agent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables in `.env`:
   ```
   GITHUB_TOKEN=your_github_token
   SONAR_TOKEN=your_sonar_token
   SONAR_URL=https://your-sonar-server.com
   OPENAI_API_KEY=your_openai_api_key
   ```

### Usage

```bash
python -m sonar_fix_agent.main --repository owner/repo --project-key your-sonar-project-key
```

## Advanced Configuration

### Customizing Fixers

You can extend the `JavaSonarFixer` class to add custom fixers for additional Sonar rules:

```python
class CustomJavaFixer(JavaSonarFixer):
    def fix_custom_rule(self, analyzer: JavaASTAnalyzer, file_path: str, issue: SonarIssue) -> bool:
        # Your custom fix implementation
        pass
```

### Performance Considerations

- The AST analysis adds some overhead but provides more accurate fixes
- For large codebases, consider running the agent on a subset of files first
- The dependency tracker caches analysis results for better performance

## Troubleshooting

### Common Issues

1. **Parser Errors**
   - Ensure your Java code compiles correctly
   - The parser may struggle with syntax errors in the source

2. **Dependency Resolution**
   - Make sure all dependencies are in the classpath
   - The agent may miss dependencies not in the standard Maven/Gradle structure

3. **Fixing Failures**
   - Check the logs for specific error messages
   - Some complex refactorings may require manual intervention

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
