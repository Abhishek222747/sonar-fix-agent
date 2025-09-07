"""
Test for the java:S1155 rule handler (Collection.isEmpty() should be used to test for emptiness).
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

# Add the parent directory to the path so we can import the module
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sonar_fix_agent.sonar_handlers import SonarHandlers
from sonar_fix_agent.java_sonar_fixer import JavaSonarFixer, SonarIssue

class TestCollectionIsEmptyRule(unittest.TestCase):
    """Test cases for the java:S1155 rule handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.test_dir = Path(tempfile.mkdtemp(prefix="sonar_fix_test_"))
        self.test_file = self.test_dir / "CollectionTest.java"
        
        # Create a test file with collection size checks
        test_code = """
import java.util.List;

public class CollectionTest {
    public boolean isListEmpty(List<String> list) {
        return list.size() == 0;
    }
    
    public boolean isListNotEmpty(List<String> list) {
        return list.size() > 0;
    }
    
    public boolean isListNotEmpty2(List<String> list) {
        return list.size() >= 1;
    }
    
    public boolean isListEmpty2(List<String> list) {
        return 0 == list.size();
    }
    
    public boolean isListNotEmpty3(List<String> list) {
        return 0 < list.size();
    }
    
    public boolean isListNotEmpty4(List<String> list) {
        return list.size() != 0;
    }
    
    public boolean isListNotEmpty5(List<String> list) {
        return 0 != list.size();
    }
}
"""
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write(test_code)
    
    def test_fix_collection_size_check(self):
        """Test that collection size checks are properly converted to isEmpty()."""
        # Test direct handler first
        fixed = SonarHandlers.fix_collection_size_check(str(self.test_file))
        self.assertTrue(fixed)
        
        # Read the fixed file
        with open(self.test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that all size() checks were replaced with isEmpty()
        self.assertIn('return list.isEmpty();', content)
        self.assertIn('return !list.isEmpty();', content)
        self.assertNotIn('list.size() == 0', content)
        self.assertNotIn('list.size() > 0', content)
        self.assertNotIn('list.size() >= 1', content)
        self.assertNotIn('0 == list.size()', content)
        self.assertNotIn('0 < list.size()', content)
        self.assertNotIn('list.size() != 0', content)
        self.assertNotIn('0 != list.size()', content)
    
    def tearDown(self):
        """Clean up test files."""
        # Remove the entire test directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

if __name__ == "__main__":
    unittest.main()
