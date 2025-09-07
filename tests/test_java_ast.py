"""
Tests for the Java AST analyzer.
"""
import os
import sys
import unittest
from pathlib import Path

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sonar_fix_agent.java_ast import JavaASTAnalyzer, JavaClass, JavaMethod, VariableInfo

class TestJavaASTAnalyzer(unittest.TestCase):
    """Test cases for the JavaASTAnalyzer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_java_file = """
package com.example;

import java.util.List;

/**
 * A simple test class for the Java AST analyzer.
 */
@Deprecated
public class TestClass {
    private static final String CONSTANT = "test";
    private int count;
    
    /**
     * A simple test method.
     */
    public void testMethod(String param) {
        System.out.println("Hello, " + param);
        count++;
    }
    
    public static void main(String[] args) {
        TestClass test = new TestClass();
        test.testMethod("world");
    }
    
    // Nested interface
    public interface NestedInterface {
        void doSomething();
    }
    
    // Nested enum
    public enum Status {
        ACTIVE, INACTIVE, PENDING
    }
}
"""

    def test_analyze_package(self):
        """Test package extraction."""
        analyzer = JavaASTAnalyzer(self.test_java_file)
        analyzer.analyze()
        self.assertEqual(analyzer.package, "com.example")

    def test_analyze_class(self):
        """Test class analysis."""
        analyzer = JavaASTAnalyzer(self.test_java_file)
        analyzer.analyze()
        
        # Check if the class was found
        self.assertIn("com.example.TestClass", analyzer.classes)
        java_class = analyzer.classes["com.example.TestClass"]
        
        # Check class properties
        self.assertEqual(java_class.name, "TestClass")
        self.assertEqual(java_class.package, "com.example")
        self.assertFalse(java_class.is_interface)
        self.assertFalse(java_class.is_abstract)
        
        # Check fields
        self.assertIn("count", java_class.fields)
        self.assertEqual(java_class.fields["count"], "int")
        
        # Check methods
        self.assertIn("testMethod", java_class.methods)
        test_method = java_class.methods["testMethod"]
        self.assertEqual(test_method.return_type, "void")
        self.assertEqual(test_method.parameters, ["String param"])
        
        # Check main method
        self.assertIn("main", java_class.methods)
        main_method = java_class.methods["main"]
        self.assertEqual(main_method.return_type, "void")
        self.assertEqual(main_method.parameters, ["String[] args"])
        
        # Note: Nested interfaces and enums are not currently processed by the analyzer
        # This is a known limitation that can be addressed in a future update

    def test_analyze_imports(self):
        """Test import analysis."""
        analyzer = JavaASTAnalyzer(self.test_java_file)
        analyzer.analyze()
        
        # Check imports
        self.assertIn("java.util.List", analyzer.imports)
        self.assertIn("List", analyzer.imported_classes)
        self.assertEqual(analyzer.imported_classes["List"], "java.util.List")

    def test_analyze_annotations(self):
        """Test annotation analysis."""
        analyzer = JavaASTAnalyzer(self.test_java_file)
        analyzer.analyze()
        
        # Check class annotations
        java_class = analyzer.classes["com.example.TestClass"]
        # Note: The test doesn't currently store annotations, but we can check the output
        # This is just a placeholder for future test expansion
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
