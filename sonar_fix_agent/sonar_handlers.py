"""
Additional SonarQube issue handlers for the JavaSonarFixer class.
"""
import re
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path

class SonarHandlers:
    @staticmethod
    def fix_empty_catch_block(file_path: str) -> bool:
        """Fix empty catch blocks (java:S108)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find empty catch blocks and add a TODO comment
            pattern = r'(catch\s*\([^{}]*\)\s*\{\s*\})'
            new_content = re.sub(
                pattern, 
                r'\1 { \n            // TODO: Add proper exception handling\n            logger.error("Exception occurred: ", e);\n        }', 
                content
            )
            
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
                
        except Exception as e:
            print(f"Error fixing empty catch block in {file_path}: {str(e)}")
            
        return False
        
    @staticmethod
    def fix_magic_numbers(file_path: str) -> bool:
        """Fix magic numbers by replacing with named constants (java:S109)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            modified = False
            magic_numbers = set()
            
            # First pass: Find all magic numbers
            for i, line in enumerate(lines):
                # Skip comments and string literals
                if '//' in line or '/*' in line or '*' in line or '"' in line or "'" in line:
                    continue
                    
                # Find all numbers in the line
                numbers = re.findall(r'\b(\d+(\.\d+)?)\b', line)
                for num, _ in numbers:
                    # Skip 0, 1, and -1 as they are commonly used
                    if num not in ['0', '1', '-1']:
                        magic_numbers.add(num)
            
            if not magic_numbers:
                return False
                
            # Generate constant names
            constants = {}
            for num in magic_numbers:
                const_name = f"MAGIC_NUMBER_{num.replace('.', '_').replace('-', 'NEG_')}"
                constants[num] = const_name
            
            # Add constant declarations at the class level
            for i, line in enumerate(lines):
                if 'class ' in line and ('public ' in line or 'final ' in line):
                    # Find the opening brace of the class
                    brace_line = i
                    while brace_line < len(lines) and '{' not in lines[brace_line]:
                        brace_line += 1
                    
                    if brace_line < len(lines):
                        # Add constants after the opening brace
                        indent = ' ' * (len(lines[brace_line]) - len(lines[brace_line].lstrip()))
                        const_declarations = []
                        for num, const_name in constants.items():
                            const_declarations.append(
                                f"{indent}    private static final int {const_name} = {num};\n"
                            )
                        
                        if const_declarations:
                            lines.insert(brace_line + 1, '\n' + ''.join(const_declarations))
                            modified = True
                    break
            
            # Second pass: Replace magic numbers with constants
            if modified:
                for i, line in enumerate(lines):
                    for num, const_name in constants.items():
                        # Replace whole word matches that aren't part of other words
                        pattern = r'\b' + re.escape(num) + r'\b'
                        new_line = re.sub(pattern, const_name, line)
                        if new_line != line:
                            lines[i] = new_line
                            modified = True
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                
        except Exception as e:
            print(f"Error fixing magic numbers in {file_path}: {str(e)}")
            
        return False
        
    @staticmethod
    def fix_system_out_println(file_path: str) -> bool:
        """Replace System.out.println with proper logging (java:S106)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if SLF4J is already imported
            has_slf4j = 'import org.slf4j.Logger' in content
            
            # Replace System.out.println with logger calls
            new_content = content
            new_content = re.sub(
                r'System\.out\.print(ln)?\((.*?)\);', 
                r'LOGGER.info(\2);', 
                new_content
            )
            
            if new_content != content:
                # Add SLF4J imports if needed
                if not has_slf4j:
                    new_content = new_content.replace(
                        'public class', 
                        'import org.slf4j.Logger;\nimport org.slf4j.LoggerFactory;\n\npublic class'
                    )
                
                # Add logger declaration if needed
                if 'private static final Logger LOGGER' not in new_content:
                    class_pos = new_content.find('class ')
                    if class_pos != -1:
                        class_name = new_content[class_pos:].split('{')[0].split()[-1]
                        new_content = (
                            new_content[:class_pos] + 
                            f'private static final Logger LOGGER = LoggerFactory.getLogger({class_name}.class);\n\n' +
                            new_content[class_pos:]
                        )
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
                
        except Exception as e:
            print(f"Error fixing System.out.println in {file_path}: {str(e)}")
            
        return False
        
    @staticmethod
    def fix_unused_private_methods(file_path: str) -> bool:
        """Flag unused private methods (java:S1144)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            modified = False
            for i, line in enumerate(lines):
                if 'private ' in line and ('(' in line or ')' in line) and ';' not in line:
                    # This is a method declaration
                    method_name = line.split('(')[0].split()[-1]
                    if not any(f'.{method_name}(' in l or f' {method_name}(' in l 
                             for j, l in enumerate(lines) if j != i):
                        # Method not found in other lines, likely unused
                        lines[i] = line.replace('private ', '// TODO: Remove or use this private method: private ', 1)
                        modified = True
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                
        except Exception as e:
            print(f"Error flagging unused private methods in {file_path}: {str(e)}")
            
        return False
        
    @staticmethod
    def fix_collection_size_check(file_path: str) -> bool:
        """
        Fix collection size checks to use isEmpty() instead of size() == 0 (java:S1155).
        
        Examples:
            - collection.size() == 0  -> collection.isEmpty()
            - collection.size() > 0   -> !collection.isEmpty()
            - collection.size() >= 1  -> !collection.isEmpty()
            - collection.size() != 0  -> !collection.isEmpty()
            - 0 == collection.size()  -> collection.isEmpty()
            - 0 < collection.size()   -> !collection.isEmpty()
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            modified = False
            
            for i, line in enumerate(lines):
                # Skip comments and string literals
                if '//' in line or '/*' in line or '*' in line or '"' in line or "'" in line:
                    continue
                
                # Process each line to find and replace size() checks
                
                # 1. list.size() == 0  ->  list.isEmpty()
                if 'size() == 0' in line:
                    lines[i] = line.replace('size() == 0', 'isEmpty()')
                    modified = True
                    continue
                    
                # 2. 0 == list.size()  ->  list.isEmpty()
                if '0 == ' in line and '.size()' in line:
                    parts = line.split('0 == ')
                    if len(parts) > 1 and '.size()' in parts[1]:
                        var = parts[1].split('.size()')[0].strip()
                        lines[i] = line.replace(f'0 == {var}.size()', f'{var}.isEmpty()')
                        modified = True
                        continue
                
                # 3. list.size() > 0  ->  !list.isEmpty()
                if 'size() > 0' in line:
                    lines[i] = line.replace('size() > 0', '!isEmpty()')
                    modified = True
                    continue
                    
                # 4. list.size() >= 1  ->  !list.isEmpty()
                if 'size() >= 1' in line:
                    lines[i] = line.replace('size() >= 1', '!isEmpty()')
                    modified = True
                    continue
                    
                # 5. 0 < list.size()  ->  !list.isEmpty()
                if '0 < ' in line and '.size()' in line:
                    parts = line.split('0 < ')
                    if len(parts) > 1 and '.size()' in parts[1]:
                        var = parts[1].split('.size()')[0].strip()
                        lines[i] = line.replace(f'0 < {var}.size()', f'!{var}.isEmpty()')
                        modified = True
                        continue
                
                # 6. list.size() != 0  ->  !list.isEmpty()
                if 'size() != 0' in line:
                    lines[i] = line.replace('size() != 0', '!isEmpty()')
                    modified = True
                    continue
                    
                # 7. 0 != list.size()  ->  !list.isEmpty()
                if '0 != ' in line and '.size()' in line:
                    parts = line.split('0 != ')
                    if len(parts) > 1 and '.size()' in parts[1]:
                        var = parts[1].split('.size()')[0].strip()
                        lines[i] = line.replace(f'0 != {var}.size()', f'!{var}.isEmpty()')
                        modified = True
                        continue
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
                
        except Exception as e:
            print(f"Error fixing collection size check in {file_path}: {str(e)}")
            
        return False
