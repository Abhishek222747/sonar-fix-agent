"""Tests for the complex issue fixer functionality."""

import unittest
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from sonar_fix_agent.complex_issue_fixer import (
    ComplexIssueFixer,
    CodeComplexityMetrics
)

class TestComplexIssueFixer(unittest.TestCase):
    """Test cases for the ComplexIssueFixer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.fixer = ComplexIssueFixer(
            openai_api_key="test_key",
            project_root=self.project_root
        )
        self.sample_java_code = """
        public class Calculator {
            public int add(int a, int b) {
                return a + b;
            }
            
            public int factorial(int n) {
                if (n <= 1) return 1;
                return n * factorial(n - 1);
            }
        }
        """
    
    def test_analyze_complexity(self):
        """Test code complexity analysis."""
        analysis = self.fixer.analyze_complexity(self.sample_java_code, "Calculator.java")
        
        # Check basic structure
        self.assertIn('methods', analysis)
        self.assertIn('classes', analysis)
        self.assertIn('dependencies', analysis)
        self.assertIn('file_metrics', analysis)
        
        # Check method analysis
        method_names = [m['name'] for m in analysis['methods']]
        self.assertTrue(any('add' in name for name in method_names), f"Expected 'add' in method names, got {method_names}")
        self.assertTrue(any('factorial' in name for name in method_names), f"Expected 'factorial' in method names, got {method_names}")
        
        # Check complexity metrics
        for method in analysis['methods']:
            if method['name'] == 'factorial':
                self.assertGreater(method['metrics']['cyclomatic_complexity'], 1)
    
    @patch('openai.ChatCompletion.create')
    def test_generate_llm_prompt(self, mock_openai):
        """Test LLM prompt generation."""
        # Mock the LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "```java\npublic class Test {}\n```"
        mock_openai.return_value = mock_response
        
        # Test with a sample issue
        issue = {
            'rule': 'java:S3776',
            'message': 'Refactor this method to reduce its Cognitive Complexity',
            'file_path': 'Calculator.java'
        }
        
        # Generate prompt and get response
        prompt = self.fixer.generate_llm_prompt(
            self.sample_java_code,
            issue,
            self.fixer.analyze_complexity(self.sample_java_code, "Calculator.java")
        )
        
        # Verify prompt contains relevant information
        self.assertIn('SonarQube', prompt)
        self.assertIn('ISSUE DETAILS', prompt)
        self.assertIn('CODE METRICS', prompt)
        self.assertIn('METHOD DETAILS', prompt)
    
    def test_extract_code_from_response(self):
        """Test code extraction from LLM response."""
        # Test with a simple code block
        response = """Here's the refactored code:
        ```java
        public class Test {
            // Implementation
        }
        ```
        """
        code = self.fixer.extract_code_from_response(response)
        self.assertIn('public class Test', code)
        
        # Test with no code block
        self.assertEqual(self.fixer.extract_code_from_response("No code here"), "")
    
    def test_validate_fix(self):
        """Test fix validation."""
        # Test with valid Java code
        valid_java = "public class Test { public static void main(String[] args) {} }"
        self.assertTrue(self.fixer._check_syntax(valid_java))
        
        # Test with invalid Java code
        invalid_java = "public class Test { invalid syntax }"
        self.assertFalse(self.fixer._check_syntax(invalid_java))

if __name__ == '__main__':
    unittest.main()
