from pathlib import Path
from typing import List, Optional

def generate_patch(file_path: str, code: str, rule: str, message: str) -> Optional[str]:
    """
    Patch generator for Java Sonar issues.
    Handles the following rules:
    - java:S1118 : Add private constructor
    - java:S1481 : Remove unused local variables
    - java:S125 : Remove commented-out code
    """
    lines = code.splitlines()
    modified = False
    changes = []  # Track changes for logging

    try:
        if rule == "java:S1118":
            # Add private constructor to utility classes
            if "class " in code and not any("private " + line.strip().split()[1] + "(" in code for line in lines if line.strip().startswith("public " + line.strip().split()[1] + "(")):
                for i, line in enumerate(lines):
                    if line.strip().startswith("public class "):
                        class_name = line.strip().split()[2].split("{")[0].strip()
                        lines.insert(i + 1, f'    private {class_name}() {{\
        // Private constructor to prevent instantiation\n        throw new UnsupportedOperationException(\"This is a utility class and cannot be instantiated\");\n    }}')
                        changes.append(f"Added private constructor to {class_name}")
                        modified = True
                        break

        elif rule == "java:S1481" or rule == "java:UnusedLocalVariable":
            # Remove unused local variables
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                if " = " in line and ";" in line and not line.strip().startswith("//"):
                    var_name = line.split("=")[0].split()[-1].strip()
                    var_used = any(var_name in l and i != j for j, l in enumerate(lines))
                    if not var_used:
                        changes.append(f"Removed unused variable: {var_name}")
                        modified = True
                        i += 1
                        continue
                new_lines.append(line)
                i += 1
            lines = new_lines

        elif rule == "java:S125":
            # Remove commented-out code blocks
            new_lines = []
            in_comment_block = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("/*"):
                    in_comment_block = True
                if not in_comment_block and not (stripped.startswith("//") and not stripped.startswith("///")):
                    new_lines.append(line)
                if in_comment_block and "*/" in line:
                    in_comment_block = False
                    changes.append("Removed commented-out code block")
                    modified = True
            lines = new_lines

        if modified:
            # Add change summary as a comment at the top
            if changes:
                change_summary = "\n".join([f" * {change}" for change in changes])
                header = f"/**\n * Automated SonarQube fixes:\n{change_summary}\n */\n"
                return header + "\n".join(lines)
            return "\n".join(lines)
        return None

    except Exception as e:
        print(f"Error generating patch for {file_path} (rule: {rule}): {str(e)}")
        return None
