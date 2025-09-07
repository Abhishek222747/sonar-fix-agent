"""
Complex Issue Fixer for SonarQube issues that require LLM-based analysis.
Handles complex issues like large methods, high cognitive complexity, and other
non-trivial code smells that can't be fixed with simple rule-based approaches.
"""

import ast
import json
import logging
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
from openai import OpenAI
import javalang
from javalang.tree import MethodDeclaration, ClassDeclaration

from .java_ast import JavaASTAnalyzer
from .java_dependency_tracker import JavaDependencyTracker as DependencyTracker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CodeComplexityMetrics:
    """Stores complexity metrics for a code unit."""
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    line_count: int = 0
    nested_blocks: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        return {
            'cyclomatic_complexity': self.cyclomatic_complexity,
            'cognitive_complexity': self.cognitive_complexity,
            'line_count': self.line_count,
            'nested_blocks': self.nested_blocks
        }

class ComplexIssueFixer:
    """Handles complex SonarQube issues using LLM-based analysis."""
    
    def __init__(self, openai_api_key: Optional[str] = None, project_root: Optional[str] = None):
        """
        Initialize the ComplexIssueFixer with optional OpenAI API key and project root.
        
        Args:
            openai_api_key: Optional API key for OpenAI services
            project_root: Optional root directory of the Java project for dependency analysis
        """
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        # Initialize without source_code, will be set in analyze_complexity
        self.ast_analyzer = None
        self.dependency_tracker = DependencyTracker(project_root=project_root or os.getcwd())
        
        # Initialize OpenAI client if API key is available
        self.openai_client = None
        if self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
    
    def analyze_complexity(self, code: str, file_path: str) -> Dict[str, Any]:
        """Analyze code complexity using AST and dependency analysis."""
        try:
            # Initialize the AST analyzer with the source code and parse it
            self.ast_analyzer = JavaASTAnalyzer(source_code=code, file_path=file_path)
            self.ast_analyzer.analyze()
            
            # Get method-level complexity metrics
            methods = []
            for class_name, java_class in self.ast_analyzer.classes.items():
                for method_name, method in java_class.methods.items():
                    method_metrics = CodeComplexityMetrics()
                    method_metrics.line_count = method.end_line - method.start_line + 1
                    # Calculate cyclomatic complexity
                    method_metrics.cyclomatic_complexity = 1  # Start with 1 for the method entry
                    # Add more complexity analysis as needed
                    
                    methods.append({
                        'name': f"{class_name}.{method_name}",
                        'metrics': method_metrics.to_dict(),
                        'start_line': method.start_line,
                        'end_line': method.end_line
                    })
            
            # Get class-level metrics
            classes = []
            for class_name, java_class in self.ast_analyzer.classes.items():
                classes.append({
                    'name': class_name,
                    'start_line': java_class.start_line,
                    'end_line': java_class.end_line
                })
            
            # Generate dependency graph
            try:
                dependencies = self.dependency_tracker.analyze_dependencies(code, file_path)
            except Exception as e:
                logger.warning(f"Could not analyze dependencies: {str(e)}")
                dependencies = {}
                
            # Return the analysis results
            return {
                'methods': methods,
                'classes': classes,
                'dependencies': dependencies,
                'file_metrics': self._calculate_file_metrics(methods)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing complexity: {str(e)}")
            return {}
    
    def _calculate_method_metrics(self, method_node: MethodDeclaration, code: str) -> CodeComplexityMetrics:
        """Calculate complexity metrics for a method."""
        metrics = CodeComplexityMetrics()
        
        # Calculate cyclomatic complexity
        metrics.cyclomatic_complexity = self._calculate_cyclomatic_complexity(method_node)
        
        # Calculate cognitive complexity (simplified)
        metrics.cognitive_complexity = self._calculate_cognitive_complexity(method_node)
        
        # Calculate line count
        start_line = method_node.position.line if hasattr(method_node, 'position') else 0
        end_line = self._get_end_line(method_node, code)
        metrics.line_count = end_line - start_line + 1 if start_line and end_line else 0
        
        return metrics
    
    def _calculate_cyclomatic_complexity(self, node) -> int:
        """Calculate cyclomatic complexity of a method."""
        complexity = 1  # Start with 1 for the method itself
        
        # Define node types that increase complexity
        complex_nodes = (
            'IfStatement', 'ForStatement', 'WhileStatement',
            'DoStatement', 'CaseStatement', 'CatchClause',
            'ConditionalExpression', 'BinaryOperation', 'ForEachStatement'
        )
        
        for _, child in node.filter(javalang.ast.Node):
            if type(child).__name__ in complex_nodes:
                complexity += 1
                
        return complexity
    
    def _calculate_cognitive_complexity(self, node) -> int:
        """Calculate cognitive complexity of a method."""
        complexity = 0
        
        def walk(node, nesting=0):
            nonlocal complexity
            
            # Increase complexity for control flow structures
            if type(node).__name__ in ('IfStatement', 'ForStatement', 'WhileStatement',
                                     'DoStatement', 'SwitchStatement', 'TryStatement',
                                     'CatchClause', 'ConditionalExpression'):
                complexity += 1 + nesting
                nesting += 1
            
            # Recursively process child nodes
            for _, child in node.filter(javalang.ast.Node):
                walk(child, nesting)
        
        walk(node)
        return complexity
    
    def _get_end_line(self, node, code: str) -> int:
        """Get the end line number of a node."""
        if hasattr(node, 'position') and hasattr(node.position, 'line'):
            return node.position.line + code.count('\n', 0, node.position.column)
        return 0
    
    def _calculate_file_metrics(self, methods: List[Dict]) -> Dict[str, int]:
        """Calculate file-level complexity metrics."""
        total_cc = sum(m['metrics']['cyclomatic_complexity'] for m in methods)
        max_cc = max((m['metrics']['cyclomatic_complexity'] for m in methods), default=0)
        
        return {
            'total_cyclomatic_complexity': total_cc,
            'max_method_cyclomatic_complexity': max_cc,
            'method_count': len(methods)
        }
    
    def generate_llm_prompt(self, code: str, issue: Dict, analysis: Dict) -> str:
        """Generate a prompt for the LLM to fix the issue."""
        prompt = """You are an expert Java code reviewer and refactoring specialist. 
Your task is to analyze and fix the following SonarQube issue in the provided code.

ISSUE DETAILS:
- Rule: {rule}
- Message: {message}
- File: {file_path}

CODE METRICS:
{metrics}

METHOD DETAILS:
{method_details}

DEPENDENCIES:
{dependencies}

ORIGINAL CODE:
```java
{code}
```

Please provide a refactored version of this code that fixes the issue while:
1. Maintaining all existing functionality
2. Following Java best practices
3. Including appropriate comments to explain the changes
4. Ensuring the code remains readable and maintainable

REFACTORED CODE:
```java
"""
        
        # Format metrics
        metrics_str = "\n".join(f"- {k}: {v}" for k, v in analysis.get('file_metrics', {}).items())
        
        # Format method details
        method_details = ""
        for method in analysis.get('methods', []):
            method_details += f"- {method['name']}:\n"
            for k, v in method['metrics'].items():
                method_details += f"  {k}: {v}\n"
        
        # Format dependencies
        deps = analysis.get('dependencies', {})
        deps_str = "\n".join(f"- {k}: {v}" for k, v in deps.items())
        
        return prompt.format(
            rule=issue.get('rule', 'Unknown'),
            message=issue.get('message', 'No message provided'),
            file_path=issue.get('file_path', 'Unknown'),
            metrics=metrics_str,
            method_details=method_details,
            dependencies=deps_str,
            code=code
        )
    
    def get_llm_response(self, prompt: str) -> str:
        """Get a response from the LLM for the given prompt."""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not provided")
        
        try:
            response = self._get_llm_response(prompt)
            return response
        except Exception as e:
            logger.error(f"Error getting LLM response: {str(e)}")
            raise
    
    def _get_llm_response(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """Get a response from the OpenAI API."""
        if not self.openai_client:
            logger.warning("OpenAI client not initialized. Skipping LLM analysis.")
            return None
            
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that fixes Java code issues."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error getting LLM response: {str(e)}")
            return None
    
    def extract_code_from_response(self, response: str) -> str:
        """Extract the refactored code from the LLM response."""
        # Look for code blocks in the response
        code_blocks = []
        in_code_block = False
        current_block = []
        
        for line in response.split('\n'):
            if line.strip() == '```java':
                in_code_block = True
                current_block = []
            elif line.strip() == '```' and in_code_block:
                in_code_block = False
                code_blocks.append('\n'.join(current_block))
            elif in_code_block:
                current_block.append(line)
        
        return code_blocks[0] if code_blocks else ""
    
    def validate_fix(self, original_code: str, fixed_code: str, test_runner) -> bool:
        """Validate that the fix doesn't break functionality."""
        try:
            # 1. Check if the code compiles
            if not self._check_syntax(fixed_code):
                return False
                
            # 2. Run tests if test_runner is provided
            if test_runner:
                test_result = test_runner.run_tests()
                if not test_result.passed:
                    return False
            
            # 3. Check if the fix actually addresses the issue
            # (This would depend on the specific issue being fixed)
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating fix: {str(e)}")
            return False
    
    def _check_syntax(self, code: str) -> bool:
        """Check if the code has valid Java syntax."""
        if not code.strip():
            return False
            
        try:
            # First check if it's a complete compilation unit
            if not any(code.strip().startswith(prefix) for prefix in 
                      ('package ', 'import ', 'public class', 'class ', 'interface ', 'enum ')):
                # Wrap in a class if it's just a method or field
                wrapped_code = f"public class TempClass {{ {code} }}"
            else:
                wrapped_code = code
                
            # Try to parse with javalang directly for better error detection
            try:
                javalang.parse.parse(wrapped_code)
                return True
            except (javalang.parser.JavaSyntaxError, javalang.tokenize.LexerError):
                return False
                
        except Exception as e:
            logger.debug(f"Syntax check failed: {str(e)}")
            return False
    
    def fix_complex_issue(self, code: str, issue: Dict, file_path: str, test_runner=None) -> Optional[str]:
        """
        Fix a complex SonarQube issue using LLM analysis.
        
        Args:
            code: The source code with the issue
            issue: Dictionary containing issue details
            file_path: Path to the file being analyzed
            test_runner: Optional test runner instance for validation
            
        Returns:
            str: The fixed code, or None if the issue couldn't be fixed
        """
        try:
            # 1. Analyze the code
            analysis = self.analyze_complexity(code, file_path)
            
            # 2. Generate LLM prompt
            prompt = self.generate_llm_prompt(code, issue, analysis)
            
            # 3. Get LLM response
            response = self.get_llm_response(prompt)
            
            # 4. Extract refactored code
            fixed_code = self.extract_code_from_response(response)
            
            if not fixed_code:
                logger.warning("No code block found in LLM response")
                return None
            
            # 5. Validate the fix
            if self.validate_fix(code, fixed_code, test_runner):
                return fixed_code
            
            return None
            
        except Exception as e:
            logger.error(f"Error fixing complex issue: {str(e)}")
            return None
