import difflib

# Replace this with your actual LLM call function
def call_llm_model(prompt: str, code: str) -> str:
    """
    Placeholder for LLM API call.
    Sends the prompt and code to your language model and returns the fixed code.
    """
    # TODO: Replace with real API call, e.g., OpenAI GPT
    # Example: return openai.ChatCompletion.create(...)

    # For testing, return code unchanged
    return code

def generate_patch(file_path: str, code: str, rule: str, message: str) -> str:
    """
    Generates a patch to fix a SonarQube issue.
    This function now tries to fix any issue, including Critical/Blocker.
    """

    prompt = f"""
You are a senior Java developer.
You are given the content of a Java file and a SonarQube issue.
File path: {file_path}

Issue:
Rule: {rule}
Message: {message}

Instructions:
- Attempt to safely fix the issue in the code.
- If it is a possible NullPointerException, add null checks.
- If it is an empty catch block, log the exception or rethrow.
- If it is a hardcoded secret, replace it with an environment variable.
- For Code Smells like unused imports or commented-out code, remove them.
- Only modify the minimal lines needed.
- Output the full fixed file content (not a diff).
"""

    # Call your LLM to get the fixed code
    fixed_code = call_llm_model(prompt, code)

    if fixed_code.strip() == code.strip():
        # No changes detected
        return None

    # Generate patch diff for git
    patch = "".join(difflib.unified_diff(
        code.splitlines(keepends=True),
        fixed_code.splitlines(keepends=True),
        fromfile=file_path,
        tofile=file_path
    ))
    return patch
