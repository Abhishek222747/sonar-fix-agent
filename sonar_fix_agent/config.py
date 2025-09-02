import os

# GitHub & Sonar tokens
MY_GITHUB_TOKEN = os.getenv("MY_GITHUB_TOKEN", "").strip()
SONAR_TOKEN = os.getenv("SONAR_TOKEN", "").strip()
SONAR_URL = os.getenv("SONAR_URL", "").strip()  # e.g., https://sonarcloud.io
SONAR_ORGANIZATION = os.getenv("SONAR_ORGANIZATION", "").strip()  # e.g., your-org-name

# OpenAI / LLM API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Max fixes per PR (batch size)
MAX_FIXES_PER_PR = 10
