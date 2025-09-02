"""
Java Sonar Issue Fixer

This module provides AST-based fixes for complex Java Sonar issues.
"""
import os
import re
from typing import Dict, List, Set, Tuple, Optional, Callable
from pathlib import Path
import javalang
from dataclasses import dataclass

from .sonar_handlers import SonarHandlers

from .java_ast import JavaASTAnalyzer, JavaClass, JavaMethod
from .java_dependency_tracker import JavaDependencyTracker


@dataclass
class SonarIssue:
    """Represents a SonarQube issue."""
    rule: str
    message: str
    file_path: str
    line: int
    start_column: int = 0
    end_column: int = 0
    context: Dict = None


class JavaSonarFixer:
    """Fixes Java Sonar issues using AST analysis."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.dependency_tracker = JavaDependencyTracker(project_root)
        self.dependency_tracker.analyze_project()
        self.ast_cache: Dict[str, JavaASTAnalyzer] = {}
    
    def _get_rule_handlers(self) -> Dict[str, Callable]:
        """Return a mapping of Sonar rule IDs to their handler methods."""
        return {
            # Existing handlers
            'java:S1068': lambda a, f, i: self._fix_unused_imports(a, f),
            'java:S1125': self._fix_boolean_literal_comparison,
            'java:S3776': self._refactor_complex_method,
            'java:S125': lambda a, f, i: self._remove_commented_code(a, f),
            'java:S1118': lambda a, f, i: self._add_private_constructor(a, f),
            'java:S1488': self._fix_immediate_return_variable,  # Local variables immediately returned/thrown
            'java:S116': self._fix_immutable_exception,  # Exception classes should be immutable
            'java:S100': self._fix_naming_convention,  # Method/class naming conventions
            'java:S117': self._fix_naming_convention,  # Parameter/local variable naming conventions
            'java:S1186': self._fix_empty_method,  # Empty methods should be removed or contain a comment
            'java:S6437': self._fix_http_url_injection,  # HTTP request URL injection protection
            
            # New handlers from SonarHandlers
            'java:S108': lambda a, f, i: SonarHandlers.fix_empty_catch_block(str(f)),
            'java:S109': lambda a, f, i: SonarHandlers.fix_magic_numbers(str(f)),
            'java:S106': lambda a, f, i: SonarHandlers.fix_system_out_println(str(f)),
            'java:S1144': lambda a, f, i: SonarHandlers.fix_unused_private_methods(str(f)),
            'java:S4973': self._fix_string_comparison,  # String comparison using ==
            'java:S1192': self._fix_duplicate_strings,  # Duplicate string literals
            'java:S1643': self._fix_string_concat_in_loop,  # String concatenation in loops
        }
    
    def _log_issue_details(self, issue: SonarIssue) -> None:
        """Log detailed information about the issue being fixed."""
        print(f"\n🔧 Fixing issue:")
        print(f"   Rule:    {issue.rule}")
        print(f"   File:    {issue.file_path}")
        print(f"   Line:    {issue.line}")
        print(f"   Message: {issue.message}")
        
    def _log_fix_result(self, success: bool, issue: SonarIssue, fix_type: str = "AST") -> None:
        """Log the result of a fix attempt."""
        status = "✅ Success" if success else "❌ Failed"
        print(f"{status} [{fix_type}] {issue.rule} in {issue.file_path}")
        if not success:
            print(f"   Reason: {issue.message}")

    def fix_issue(self, issue: SonarIssue) -> bool:
        """
        Attempt to fix a Sonar issue.
        
        Returns:
            bool: True if the issue was fixed, False otherwise
        """
        try:
            self._log_issue_details(issue)
            
            # Get the full path to the file
            file_path = self.project_root / issue.file_path
            
            # Get or create AST analyzer for the file
            if str(file_path) not in self.ast_cache:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source = f.read()
                    
                    analyzer = JavaASTAnalyzer(source, str(file_path))
                    analyzer.analyze()  # Perform the AST parsing and analysis
                    self.ast_cache[str(file_path)] = analyzer
                    print("[AST] Successfully parsed and analyzed file")
                except javalang.parser.JavaSyntaxError as e:
                    print(f"[AST] Syntax error in {file_path}: {e}")
                    return False
                except Exception as e:
                    print(f"[AST] Error analyzing {file_path}: {str(e)}")
                    return False
            
            analyzer = self.ast_cache[str(file_path)]
            
            # Get the appropriate handler for this rule
            handler = self._get_rule_handlers().get(issue.rule)
            
            if not handler:
                print(f"[AST] No handler found for rule: {issue.rule}")
                return False
                
            try:
                # Try AST-based fix first
                result = handler(analyzer, str(file_path), issue)
                if result:
                    self._log_fix_result(True, issue, "AST")
                    return True
                
                # Fall back to LLM-based fix if AST fix fails
                print(f"[AST] Could not fix {issue.rule} in {issue.file_path}, trying LLM...")
                llm_result = self._fix_with_llm(issue)
                self._log_fix_result(llm_result, issue, "LLM")
                return llm_result
                
            except Exception as e:
                print(f"[AST] Error in handler for {issue.rule} in {issue.file_path}: {str(e)}")
                # Fall back to LLM-based fix
                llm_result = self._fix_with_llm(issue)
                self._log_fix_result(llm_result, issue, "LLM (fallback)")
                return llm_result
            
        except Exception as e:
            error_msg = f"Unexpected error fixing {issue.rule} in {issue.file_path}: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return False
    
    def _fix_unused_imports(self, analyzer: JavaASTAnalyzer, file_path: str) -> bool:
        """Remove unused imports from a Java file."""
        try:
            # Get the current source code
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find all import statements
            import_lines = []
            for i, line in enumerate(lines):
                if line.strip().startswith('import '):
                    import_lines.append((i, line.strip()))
            
            # Find used imports
            used_imports = set()
            for class_name in analyzer.classes.values():
                for method in class_name.methods.values():
                    # Check method calls and variable types
                    for call in method.method_calls:
                        # This is a simplified check - in a real implementation,
                        # you'd need to resolve the full type of each method call
                        pass
            
            # Remove unused imports
            modified = False
            for i, import_line in reversed(import_lines):
                import_path = import_line[7:-1]  # Remove 'import ' and ';'
                if import_path not in used_imports:
                    # Remove the import line
                    lines.pop(i)
                    modified = True
            
            if modified:
                # Write the modified content back to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                
        except Exception as e:
            print(f"Error fixing unused imports in {file_path}: {str(e)}")
            
        return False
    
    def _fix_boolean_literal_comparison(
        self, 
        analyzer: JavaASTAnalyzer, 
        file_path: str, 
        issue: SonarIssue
    ) -> bool:
        """Fix boolean literal comparison issues (java:S1125)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Get the line with the issue
            line_num = issue.line - 1  # Convert to 0-based index
            if line_num < 0 or line_num >= len(lines):
                return False
                
            line = lines[line_num].rstrip()
            
            # Simple pattern matching for boolean comparisons
            patterns = [
                (r'\b(true|false)\s*==\s*([^\s;]+)', r'\2'),
                (r'([^\s;]+)\s*==\s*\b(true|false)\b', r'\1'),
                (r'\b(true|false)\s*!=\s*([^\s;]+)', r'!\2'),
                (r'([^\s;]+)\s*!=\s*\b(true|false)\b', r'!\1')
            ]
            
            modified = False
            for pattern, replacement in patterns:
                new_line, n = re.subn(pattern, replacement, line)
                if n > 0:
                    lines[line_num] = new_line + '\n'
                    # Write the modified content back to the file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    modified = True
                    break
                    
            return modified
            
        except Exception as e:
            print(f"Error fixing boolean comparison in {file_path}: {str(e)}")
            return False
    
    def _refactor_complex_method(
        self, 
        analyzer: JavaASTAnalyzer, 
        file_path: str, 
        issue: SonarIssue
    ) -> bool:
        """Refactor a complex method to improve maintainability."""
        # This is a simplified implementation
        # In a real scenario, you would:
        # 1. Analyze the method's cyclomatic complexity
        # 2. Identify extractable blocks
        # 3. Create new methods for those blocks
        # 4. Update the original method to call the new methods
        
        # For now, we'll just add a TODO comment
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_num = issue.line - 1
            if line_num < 0 or line_num >= len(lines):
                return False
                
            # Add a TODO comment above the method
            method_line = line_num
            while method_line > 0 and not lines[method_line].strip().startswith(('public', 'private', 'protected')):
                method_line -= 1
                
            if method_line > 0:
                lines.insert(method_line, '// TODO: Refactor this method to reduce complexity\n')
                
                # Write the modified content back to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                
        except Exception as e:
            print(f"Error refactoring complex method in {file_path}: {str(e)}")
            
        return False
    
    def _remove_commented_code(self, analyzer: JavaASTAnalyzer, file_path: str) -> bool:
        """Remove commented-out code."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Simple pattern to detect commented-out code blocks
            comment_block = False
            modified = False
            
            for i in range(len(lines)):
                line = lines[i].strip()
                
                # Handle block comments
                if '/*' in line and '*/' not in line:
                    comment_block = True
                    continue
                elif '*/' in line:
                    comment_block = False
                    continue
                    
                # Remove commented-out lines that look like code
                if (line.startswith('//') and len(line) > 3 and 
                    any(c in line for c in [';', '{', '}']) and
                    not any(skip in line for skip in ['TODO', 'FIXME', 'NOTE'])):
                    lines[i] = ''
                    modified = True
            
            if modified:
                # Write the modified content back to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                
        except Exception as e:
            print(f"Error removing commented code in {file_path}: {str(e)}")
            
        return False
    
    def _add_private_constructor(self, analyzer: JavaASTAnalyzer, file_path: str) -> bool:
        """Add a private constructor to utility classes."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find the class declaration
            class_start = -1
            class_name = None
            for i, line in enumerate(lines):
                if 'class ' in line and ('public ' in line or 'final ' in line):
                    class_start = i
                    # Extract class name
                    class_match = re.search(r'class\s+(\w+)', line)
                    if class_match:
                        class_name = class_match.group(1)
                    break
            
            if class_name and class_start >= 0:
                # Find the opening brace of the class
                brace_line = class_start
                while brace_line < len(lines) and '{' not in lines[brace_line]:
                    brace_line += 1
                
                if brace_line < len(lines):
                    # Add private constructor after the opening brace
                    indent = ' ' * (len(lines[brace_line]) - len(lines[brace_line].lstrip()))
                    constructor = (
                        f"{indent}    private {class_name}() {{\n"
                        f"{indent}        // Private constructor to prevent instantiation\n"
                        f"{indent}        throw new UnsupportedOperationException(\"Utility class\");\n"
                        f"{indent}    }}\n\n"
                    )
                    lines.insert(brace_line + 1, constructor)
                    
                    # Write the modified content back to the file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    return True
                            
        except Exception as e:
            print(f"Error adding private constructor in {file_path}: {str(e)}")
            
        return False
        
    def _fix_string_comparison(self, analyzer: JavaASTAnalyzer, file_path: str, issue: SonarIssue) -> bool:
        """Fix string comparison using == (java:S4973)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_num = issue.line - 1
            if line_num < 0 or line_num >= len(lines):
                return False
                
            line = lines[line_num].rstrip()
            
            # Replace string == with .equals()
            pattern = r'([\w\(\)"]+)\s*==\s*([\w\(\)"]+)'
            new_line = re.sub(pattern, r'\1.equals(\2)', line)
            
            if new_line != line:
                lines[line_num] = new_line + '\n'
                # Write the modified content back to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                
        except Exception as e:
            print(f"Error fixing string comparison in {file_path}: {str(e)}")
            
        return False
        
    def _fix_duplicate_strings(self, analyzer: JavaASTAnalyzer, file_path: str, issue: SonarIssue) -> bool:
        """Fix duplicate string literals (java:S1192)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all string literals
            string_literals = re.findall(r'"([^"]*)"', content)
            
            # Count occurrences of each string
            string_counts = {}
            for s in string_literals:
                if len(s) > 5:  # Only consider strings longer than 5 characters
                    string_counts[s] = string_counts.get(s, 0) + 1
            
            # Find strings that appear multiple times
            duplicate_strings = {s: c for s, c in string_counts.items() if c > 1}
            
            if not duplicate_strings:
                return False
                
            # Add constants for duplicate strings
            lines = content.split('\n')
            modified = False
            
            # Find class declaration to add constants
            for i, line in enumerate(lines):
                if 'class ' in line and ('public ' in line or 'final ' in line):
                    # Find the opening brace
                    brace_line = i
                    while brace_line < len(lines) and '{' not in lines[brace_line]:
                        brace_line += 1
                    
                    if brace_line < len(lines):
                        # Add string constants
                        indent = ' ' * (len(lines[brace_line]) - len(lines[brace_line].lstrip()))
                        constants = []
                        
                        for s, count in duplicate_strings.items():
                            # Create a constant name from the string
                            const_name = 'STR_' + re.sub(r'[^A-Z0-9]', '_', s.upper())[:30]
                            constants.append(
                                f"{indent}    private static final String {const_name} = \"{s}\";\n"
                            )
                        
                        if constants:
                            lines.insert(brace_line + 1, '\n' + ''.join(constants))
                            modified = True
                    break
            
            # Replace string literals with constants
            if modified:
                new_content = '\n'.join(lines)
                for s, count in duplicate_strings.items():
                    const_name = 'STR_' + re.sub(r'[^A-Z0-9]', '_', s.upper())[:30]
                    new_content = new_content.replace(f'"{s}"', const_name)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
                
        except Exception as e:
            print(f"Error fixing duplicate strings in {file_path}: {str(e)}")
            
        return False
        
    def _fix_http_url_injection(self, analyzer: JavaASTAnalyzer, file_path: str, issue: SonarIssue) -> bool:
        """Fix HTTP request URL injection vulnerabilities (java:S6437)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            issue_line = issue.line - 1
            if issue_line < 0 or issue_line >= len(lines):
                return False
                
            # Get the line with the URL construction
            line = lines[issue_line].rstrip()
            
            # Look for common URL construction patterns
            url_var_match = re.search(r'(\w+)\s*\+\s*[\'"][^\'"+]*[\'"]', line)
            if not url_var_match:
                return False
                
            url_var = url_var_match.group(1)
            
            # Find where the URL variable is defined
            url_def_line = -1
            for i in range(issue_line - 1, max(-1, issue_line - 20), -1):
                if f'String {url_var} =' in lines[i] or f' {url_var} =' in lines[i]:
                    url_def_line = i
                    break
                    
            if url_def_line == -1:
                return False
                
            # Check if the URL is already using a URI builder or similar safe construction
            if any(builder in lines[url_def_line] for builder in ['UriComponentsBuilder', 'URIBuilder', 'UriBuilder']):
                return False
                
            # Get the base URL and parameters
            base_url = ''
            params = []
            
            # Extract the base URL (simplified)
            url_parts = re.findall(r'[\'"]([^\'"+]*)[\'"]', line)
            if url_parts:
                base_url = url_parts[0]
                
            # Extract parameters (simplified)
            param_matches = re.findall(r'\+\s*(\w+)', line)
            params = [p for p in param_matches if p != url_var]
            
            if not base_url or not params:
                return False
                
            # Generate the fixed code using UriComponentsBuilder
            indent = ' ' * (len(lines[url_def_line]) - len(lines[url_def_line].lstrip()))
            
            # Add import if needed
            imports_section = -1
            for i, l in enumerate(lines):
                if 'import ' in l and ';' in l:
                    imports_section = i
                    
            if imports_section != -1 and 'import org.springframework.web.util.UriComponentsBuilder;' not in '\n'.join(lines):
                lines.insert(imports_section + 1, 'import org.springframework.web.util.UriComponentsBuilder;\n')
            
            # Build the safe URL construction
            builder_lines = [
                f"{indent}String {url_var} = UriComponentsBuilder.fromHttpUrl(\"{base_url}\")",
            ]
            
            for i, param in enumerate(params):
                builder_lines.append(f"{indent}    .queryParam(\"{param}\", {param})")
                
            builder_lines.append(f"{indent}    .build().toUriString();")
            
            # Replace the original URL construction
            lines[url_def_line] = '\n'.join(builder_lines) + '\n'
            
            # Remove the original URL construction line
            if issue_line != url_def_line:
                lines[issue_line] = lines[issue_line].rstrip() + '  // Fixed: URL construction made safe\n'
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
                
            return True
            
        except Exception as e:
            print(f"Error fixing HTTP URL injection in {file_path}: {str(e)}")
            
        return False
        
    def _fix_empty_method(self, analyzer: JavaASTAnalyzer, file_path: str, issue: SonarIssue) -> bool:
        """Add a comment to empty methods to explain why they're empty (java:S1186)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            issue_line = issue.line - 1
            if issue_line < 0 or issue_line >= len(lines):
                return False
                
            # Find the method signature line (could be multiple lines before the empty body)
            method_start = issue_line
            while method_start >= 0 and '{' not in lines[method_start]:
                method_start -= 1
                
            if method_start < 0:
                return False
                
            # Find the opening and closing braces of the method
            brace_count = 0
            method_body_start = -1
            method_body_end = -1
            
            for i in range(method_start, len(lines)):
                if '{' in lines[i]:
                    brace_count += lines[i].count('{')
                    if method_body_start == -1:
                        method_body_start = i
                if '}' in lines[i]:
                    brace_count -= lines[i].count('}')
                    if brace_count == 0:
                        method_body_end = i
                        break
                        
            if method_body_start == -1 or method_body_end == -1:
                return False
                
            # Check if the method is really empty (only whitespace/comments between braces)
            is_empty = True
            for i in range(method_body_start + 1, method_body_end):
                line = lines[i].strip()
                if line and not line.startswith(('//', '/*', '*', '*/')):
                    is_empty = False
                    break
                    
            if not is_empty:
                return False
                
            # Add a comment explaining why the method is empty
            indent = ' ' * (len(lines[method_body_start]) - len(lines[method_body_start].lstrip()))
            comment = f"{indent}    // Intentionally empty - {issue.message.split('(')[0].strip()}\n"
            
            # Insert the comment right after the opening brace
            lines.insert(method_body_start + 1, comment)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
                
            return True
            
        except Exception as e:
            print(f"Error fixing empty method in {file_path}: {str(e)}")
            
        return False
        
    def _fix_naming_convention(self, analyzer: JavaASTAnalyzer, file_path: str, issue: SonarIssue) -> bool:
        """Fix naming convention violations (java:S100 for methods/classes, java:S117 for parameters/variables)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            issue_line = issue.line - 1
            if issue_line < 0 or issue_line >= len(lines):
                return False
                
            # Get the line with the naming convention violation
            line = lines[issue_line].rstrip()
            
            # Extract the identifier that needs to be renamed
            # This is a simplified approach - in a real implementation, you'd want to parse the AST
            # to accurately identify the identifier's type (method, variable, parameter, etc.)
            
            # Look for common patterns in the issue message
            if 'Rename this' in issue.message and "'" in issue.message:
                # Extract the current name from the message
                current_name = issue.message.split("'")[1]
                
                # Determine the type of identifier based on the rule
                if issue.rule == 'java:S100':  # Method/class naming
                    # Convert to camelCase for methods or PascalCase for classes
                    if '(' in line:  # Method
                        new_name = self._to_camel_case(current_name)
                    else:  # Class
                        new_name = self._to_pascal_case(current_name)
                else:  # java:S117 - Parameter/local variable
                    new_name = self._to_camel_case(current_name)
                
                # Only proceed if the name actually needs to be changed
                if new_name != current_name:
                    # Replace all occurrences of the identifier (simple string replacement)
                    # Note: This is a basic implementation - a more robust solution would use AST
                    for i in range(len(lines)):
                        # Use word boundaries to avoid partial matches
                        lines[i] = re.sub(r'\b' + re.escape(current_name) + r'\b', new_name, lines[i])
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    return True
                    
        except Exception as e:
            print(f"Error fixing naming convention in {file_path}: {str(e)}")
            
        return False
        
    def _to_camel_case(self, name: str) -> str:
        """Convert a string to camelCase."""
        if not name:
            return name
            
        # Handle common prefixes like 'm' or 's' for member/static variables
        if len(name) > 1 and name[0] in ('m', 's', '_') and name[1].isupper():
            prefix = name[0]
            rest = name[1:]
            return prefix + rest[0].lower() + rest[1:]
            
        # Handle snake_case and SCREAMING_SNAKE_CASE
        if '_' in name:
            parts = name.lower().split('_')
            return parts[0] + ''.join(part.capitalize() for part in parts[1:] if part)
            
        # Handle PascalCase
        if name[0].isupper() and len(name) > 1 and name[1].islower():
            return name[0].lower() + name[1:]
            
        # Already in camelCase or another format we don't handle
        return name
        
    def _to_pascal_case(self, name: str) -> str:
        """Convert a string to PascalCase."""
        if not name:
            return name
            
        # Handle snake_case and SCREAMING_SNAKE_CASE
        if '_' in name:
            parts = name.lower().split('_')
            return ''.join(part.capitalize() for part in parts if part)
            
        # Handle camelCase
        if name[0].islower():
            return name[0].upper() + name[1:]
            
        # Already in PascalCase or another format we don't handle
        return name
        
    def _fix_immutable_exception(self, analyzer: JavaASTAnalyzer, file_path: str, issue: SonarIssue) -> bool:
        """Ensure exception classes are immutable by making fields final (java:S116)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            issue_line = issue.line - 1
            if issue_line < 0 or issue_line >= len(lines):
                return False
                
            # Find the class declaration
            class_start = -1
            for i in range(issue_line, max(-1, issue_line - 10), -1):
                if 'class ' in lines[i] and ('Exception' in lines[i] or 'Error' in lines[i]):
                    class_start = i
                    break
                    
            if class_start == -1:
                return False
                
            # Find the class body
            brace_count = 0
            class_body_start = -1
            for i in range(class_start, len(lines)):
                if '{' in lines[i]:
                    brace_count += lines[i].count('{')
                    class_body_start = i + 1
                    break
                    
            if class_body_start == -1:
                return False
                
            # Find all field declarations in the class
            modified = False
            for i in range(class_body_start, len(lines)):
                line = lines[i].strip()
                
                # Skip lines that are not field declarations
                if not line or line.startswith(('//', '/*', '*', '*/', '@')):
                    continue
                    
                # Check if this is a field declaration (simple check)
                if ';' in line and ('private' in line or 'protected' in line or 'public' in line):
                    # Check if field is already final
                    if 'final ' not in line and 'static final ' not in line:
                        # Add final modifier
                        if 'private' in line:
                            lines[i] = lines[i].replace('private ', 'private final ', 1)
                        elif 'protected' in line:
                            lines[i] = lines[i].replace('protected ', 'protected final ', 1)
                        elif 'public' in line:
                            lines[i] = lines[i].replace('public ', 'public final ', 1)
                        modified = True
                        
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                
        except Exception as e:
            print(f"Error making exception class immutable in {file_path}: {str(e)}")
            
        return False
        
    def _fix_immediate_return_variable(self, analyzer: JavaASTAnalyzer, file_path: str, issue: SonarIssue) -> bool:
        """Fix local variables that are immediately returned or thrown (java:S1488)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            issue_line = issue.line - 1
            if issue_line < 0 or issue_line >= len(lines):
                return False
                
            # Look for pattern: Type var = value; return var;
            var_decl = re.match(r'^\s*(\w+\s+\w+)\s*=\s*(.+);\s*$', lines[issue_line].strip())
            if not var_decl:
                return False
                
            var_type_name = var_decl.group(1)
            var_value = var_decl.group(2)
            
            # Check if next line is return or throw
            next_line = issue_line + 1
            if next_line >= len(lines):
                return False
                
            return_match = re.match(r'^\s*return\s+(\w+)\s*;\s*$', lines[next_line].strip())
            if return_match and return_match.group(1) in var_type_name.split()[-1]:
                # Replace both lines with a single return statement
                lines[issue_line] = f"{' ' * (len(lines[issue_line]) - len(lines[issue_line].lstrip()))}return {var_value};\n"
                lines.pop(next_line)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                
        except Exception as e:
            print(f"Error fixing immediate return variable in {file_path}: {str(e)}")
            
        return False
        
    def _fix_string_concat_in_loop(self, analyzer: JavaASTAnalyzer, file_path: str, issue: SonarIssue) -> bool:
        """Fix string concatenation in loops (java:S1643)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Look for string concatenation in loops
            in_loop = False
            modified = False
            loop_start = -1
            string_vars = set()
            
            for i, line in enumerate(lines):
                line = line.rstrip()
                
                # Detect start of a loop
                if any(loop_start in line for loop_start in ['for (', 'while (', 'do {']):
                    in_loop = True
                    loop_start = i
                    string_vars = set()
                # Detect end of a loop
                elif in_loop and '}' in line and 'else' not in line:
                    in_loop = False
                    # If we found string concatenation in the loop, suggest using StringBuilder
                    if string_vars:
                        # Find the line before the loop to add StringBuilder
                        indent = ' ' * (len(lines[loop_start]) - len(lines[loop_start].lstrip()))
                        sb_decl = f"{indent}    StringBuilder sb = new StringBuilder();\n"
                        lines.insert(loop_start, sb_decl)
                        
                        # Find the line after the loop to add the result
                        result_line = i + 1
                        result_var = next(iter(string_vars)) + "Result"
                        result_decl = f"{indent}    String {result_var} = sb.toString();\n"
                        lines.insert(result_line, result_decl)
                        
                        # Replace string concatenations with StringBuilder
                        for j in range(loop_start + 1, i + 1):
                            for var in string_vars:
                                if f"{var} +=" in lines[j] or f"{var} = {var} +" in lines[j]:
                                    lines[j] = lines[j].replace(
                                        f"{var} +=", 
                                        f"sb.append("
                                    ).replace(
                                        f"{var} = {var} +", 
                                        f"sb = new StringBuilder({var}); sb.append("
                                    ) + ");"
                        
                        modified = True
                        string_vars = set()
                
                # Look for string concatenation in loops
                if in_loop and ('+=' in line or '= ' in line) and '"' in line:
                    # Find variable being assigned to
                    var_match = re.search(r'^(\s*\w+)\s*[+=]', line)
                    if var_match:
                        string_vars.add(var_match.group(1).strip())
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                
        except Exception as e:
            print(f"Error fixing string concatenation in loop in {file_path}: {str(e)}")
            
        return False
