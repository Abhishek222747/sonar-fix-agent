import openai
from .config import OPENAI_API_KEY, MAX_FIX_LINES

openai.api_key = OPENAI_API_KEY

def generate_patch(file_path, code_snippet, rule, message):
    prompt = f"""
You are a Java code fixer. 

Rule: {rule}
Message: {message}
File: {file_path}
Code snippet:
{code_snippet}

Task:
- Produce a small unified diff to fix the issue.
- Do not change unrelated code.
- Keep changes under {MAX_FIX_LINES} lines.
- If unsure, return EXACTLY: NO_FIX
"""
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    text = response['choices'][0]['message']['content'].strip()
    if "NO_FIX" in text:
        return None
    return text
