from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import re
import random
import string
import json

class CredentialManager:
    """Manages sensitive credentials and their secure storage."""
    
    @staticmethod
    def generate_secure_password(length: int = 32) -> str:
        """Generate a secure random password."""
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.SystemRandom().choice(chars) for _ in range(length))
    
    @staticmethod
    def is_potential_credential(value: str) -> bool:
        """Check if a string looks like a hardcoded credential."""
        credential_indicators = ['pass', 'pwd', 'secret', 'key', 'token', 'credential']
        value_lower = value.lower()
        return any(indicator in value_lower for indicator in credential_indicators)

def generate_patch(file_path: str, code: str, rule: str, message: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Patch generator for Java Sonar issues using a hybrid approach.
    
    Args:
        file_path: Path to the file being analyzed
        code: The source code to analyze
        rule: SonarQube rule key (e.g., 'java:S2190')
        message: The SonarQube issue message
        context: Additional context about the issue
        
    Returns:
        str: The patched code, or None if no fix was applied
    """
    # Handle different rules with appropriate fixers
    fixer_map = {
        'java:S2190': fix_infinite_recursion,
        'java:S6437': fix_hardcoded_credentials,
        'java:S6703': fix_database_credentials,
        'java:S1118': fix_utility_class,
        'java:S1481': fix_unused_variables,
        'java:S125': fix_commented_code
    }
    
    fixer = fixer_map.get(rule)
    if fixer:
        return fixer(code, message, context or {})
    return None
def fix_infinite_recursion(code: str, message: str, context: Dict[str, Any]) -> Optional[str]:
    """
    Fix infinite recursion issues (S2190) by adding a base case or proper termination condition.
    
    Args:
        code: The source code to analyze
        message: The SonarQube issue message
        context: Additional context about the issue
        
    Returns:
        str: The patched code, or None if no fix was applied
    """
    lines = code.splitlines()
    modified = False
    
    # Look for recursive method calls and add proper termination
    for i, line in enumerate(lines):
        if 'return' in line and '(' in line and ')' in line:
            # Simple case: Add a base case before the recursive call
            method_name_match = re.search(r'(\w+)\s*\(', line)
            if method_name_match:
                method_name = method_name_match.group(1)
                # Add a base case check before the recursive call
                base_case = f'if (baseCaseCondition) {{ return baseCaseValue; }}  // Added base case to prevent infinite recursion'
                lines.insert(i, '    ' + base_case)
                modified = True
                break
    
    return '\n'.join(lines) if modified else None

def fix_hardcoded_credentials(code: str, message: str, context: Dict[str, Any]) -> Optional[str]:
    """
    Fix hardcoded credentials issues (S6437) by replacing them with environment variables.
    
    Args:
        code: The source code to analyze
        message: The SonarQube issue message
        context: Additional context about the issue
        
    Returns:
        str: The patched code, or None if no fix was applied
    """
    lines = code.splitlines()
    modified = False
    credential_manager = CredentialManager()
    
    # Pattern to find potential credential assignments
    credential_pattern = re.compile(r'(\w+\s*=\s*["\'])([^"\']*?)(["\'])')
    
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in ['pass', 'pwd', 'secret', 'key']):
            matches = list(credential_pattern.finditer(line))
            for match in matches:
                prefix, value, suffix = match.groups()
                if credential_manager.is_potential_credential(prefix) or credential_manager.is_potential_credential(value):
                    # Replace with environment variable
                    env_var_name = f"{prefix.split('=')[0].strip().upper()}_PASSWORD"
                    new_line = line[:match.start()] + f"{prefix}" + f'System.getenv(\"{env_var_name}\")' + line[match.end():]
                    lines[i] = new_line
                    modified = True
                    
                    # Add a comment about setting the environment variable
                    comment = f"// Set {env_var_name} environment variable with a secure password"
                    lines.insert(i, comment)
                    break
    
    return '\n'.join(lines) if modified else None

def fix_database_credentials(code: str, message: str, context: Dict[str, Any]) -> Optional[str]:
    """
    Fix database credential issues (S6703) by using a secure configuration approach.
    
    Args:
        code: The source code to analyze
        message: The SonarQube issue message
        context: Additional context about the issue
        
    Returns:
        str: The patched code, or None if no fix was applied
    """
    lines = code.splitlines()
    modified = False
    
    # Pattern to find JDBC URLs and credentials
    jdbc_pattern = re.compile(r'(jdbc:[^"\']+)["\']')
    user_pattern = re.compile(r'(user(name)?\s*=\s*["\'])([^"\']*)(["\'])', re.IGNORECASE)
    pass_pattern = re.compile(r'((password|pwd)\s*=\s*["\'])([^"\']*)(["\'])', re.IGNORECASE)
    
    for i, line in enumerate(lines):
        if 'jdbc:' in line.lower():
            # Replace JDBC URL with environment variable
            jdbc_match = jdbc_pattern.search(line)
            if jdbc_match:
                url_var = 'DB_URL'
                lines[i] = line.replace(jdbc_match.group(0), f'"' + '${' + url_var + '}"')
                modified = True
                
                # Add a comment about configuration
                comment = '// Configure database URL in application properties or environment variables'
                lines.insert(i, comment)
                
        # Replace username/password with environment variables
        if any(keyword in line.lower() for keyword in ['user', 'password', 'pwd']):
            if user_pattern.search(line):
                user_var = 'DB_USERNAME'
                lines[i] = user_pattern.sub(r'\1' + '${' + user_var + '}' + r'\4', line)
                modified = True
                
                # Add a comment about configuration
                comment = '// Configure database credentials in environment variables or secure vault'
                lines.insert(i, comment)
                
            if pass_pattern.search(line):
                pass_var = 'DB_PASSWORD'
                lines[i] = pass_pattern.sub(r'\1' + '${' + pass_var + '}' + r'\4', line)
                modified = True
    
    return '\n'.join(lines) if modified else None

def fix_utility_class(code: str, message: str, context: Dict[str, Any]) -> Optional[str]:
    """
    Add private constructor to utility classes (S1118).
    """
    lines = code.splitlines()
    
    if "class " in code and not any("private " + line.strip().split()[1] + "(" in code 
                                 for line in lines if line.strip().startswith("public " + line.strip().split()[1] + "(")):
        for i, line in enumerate(lines):
            if line.strip().startswith("public class "):
                class_name = line.strip().split()[2].split("{")[0].strip()
                lines.insert(i + 1, f'    private {class_name}() {{\n        // Private constructor to prevent instantiation\n        throw new UnsupportedOperationException(\"This is a utility class and cannot be instantiated\");\n    }}')
                return '\n'.join(lines)
    return None

def fix_unused_variables(code: str, message: str, context: Dict[str, Any]) -> Optional[str]:
    """
    Remove unused local variables (S1481).
    """
    lines = code.splitlines()
    new_lines = []
    modified = False
    i = 0
    
    while i < len(lines):
        line = lines[i]
        if " = " in line and ";" in line and not line.strip().startswith("//"):
            var_name = line.split("=")[0].split()[-1].strip()
            var_used = any(var_name in l and i != j for j, l in enumerate(lines))
            if not var_used:
                modified = True
                i += 1
                continue
        new_lines.append(line)
        i += 1
    
    return '\n'.join(new_lines) if modified else None

def fix_commented_code(code: str, message: str, context: Dict[str, Any]) -> Optional[str]:
    """
    Remove commented-out code (S125).
    """
    lines = code.splitlines()
    new_lines = []
    modified = False
    in_comment_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("/*"):
            in_comment_block = True
        if not in_comment_block and not stripped.startswith("//"):
            new_lines.append(line)
        if in_comment_block and "*/" in line:
            in_comment_block = False
    
    if len(new_lines) < len(lines):
        return '\n'.join(new_lines)
    return None
    
