import os

# GitHub & Sonar tokens
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SONAR_TOKEN = os.getenv("SONAR_TOKEN")
SONAR_URL = os.getenv("SONAR_URL")  # e.g., https://sonarcloud.io

# OpenAI / LLM API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Max fixes per PR (batch size)
MAX_FIXES_PER_PR = 3
