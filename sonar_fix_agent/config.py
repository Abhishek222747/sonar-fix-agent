from dotenv import load_dotenv
import os

# Load variables from .env file
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SONAR_TOKEN = os.getenv("SONAR_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SONAR_URL = os.getenv("SONAR_URL", "https://sonarcloud.io")
MAX_FIX_LINES = int(os.getenv("MAX_FIX_LINES", "10"))

# Debug prints to verify environment variables
print("GITHUB_TOKEN loaded:", bool(GITHUB_TOKEN))
print("SONAR_TOKEN loaded:", bool(SONAR_TOKEN))
print("OPENAI_API_KEY loaded:", bool(OPENAI_API_KEY))
print("SONAR_URL loaded:", SONAR_URL)
print("MAX_FIX_LINES:", MAX_FIX_LINES)
