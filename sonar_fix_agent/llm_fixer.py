import difflib

def call_llm_model(prompt: str, code: str) -> str:
    """
    Replace this with your actual LLM API call (OpenAI, GPT, etc.)
    """
    # TODO: Implement real API call
    return code  # placeholder for testing

def generate_patch(file_path: str, code: str, rule: str, message: str) -> str:
    prompt = f"""
You are a senior Java developer.
File: {file_path}
Sonar rule: {rule}
Message: {message}

Instructions:
- Fix the issue safely.
- NullPointerException → add null checks
- Empty catch → log or rethrow
- Hardcoded secrets → use env variables
- Code smells → remove unused imports / commented code
- Minimal changes, output full fixed file
"""
    fixed_code = call_llm_model(prompt, code)
    if fixed_code.strip() == code.strip():
        return None
    return "".join(difflib.unified_diff(
        code.splitlines(keepends=True),
        fixed_code.splitlines(keepends=True),
        fromfile=file_path,
        tofile=file_path
    ))
