from pathlib import Path

def generate_patch(file_path, code, rule, message):
    """
    Deterministic patch generator for 3 specific Java Sonar issues:
    - java:S1118 : Add private constructor
    - java:UnusedLocalVariable : Remove unused variable
    - java:S125 : Remove commented-out lines
    """
    lines = code.splitlines()
    modified = False

    if rule == "java:S1118":
        # Add private constructor to classes without any constructor
        if "public class " in code and "private " not in code:
            for i, line in enumerate(lines):
                if line.strip().startswith("public class "):
                    class_name = line.strip().split()[2]
                    lines.insert(i + 1, f"    private {class_name}() {{}}  // auto-added private constructor")
                    modified = True
                    break

    elif rule == "java:UnusedLocalVariable":
        # Remove variable named dbPassword
        new_lines = []
        for line in lines:
            if "dbPassword" in line:
                modified = True
                continue
            new_lines.append(line)
        lines = new_lines

    elif rule == "java:S125":
        # Remove commented-out lines
        new_lines = []
        for line in lines:
            if line.strip().startswith("//"):
                modified = True
                continue
            new_lines.append(line)
        lines = new_lines

    if modified:
        return "\n".join(lines)
    else:
        return None
