from dotenv import load_dotenv
import os

# Load variables from .env file
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SONAR_TOKEN = os.getenv("SONAR_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SONAR_URL = os.getenv("SONAR_URL", "https://sonarcloud.io")
MAX_FIX_LINES = int(os.getenv("MAX_FIX_LINES", "10"))
