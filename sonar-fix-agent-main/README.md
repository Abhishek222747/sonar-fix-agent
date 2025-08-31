An intelligent agent that automatically fixes SonarQube/SonarCloud issues in your codebase using AI. The agent analyzes your code, identifies issues, and creates pull requests with fixes, helping you maintain high code quality with minimal effort.

## 🌟 Features

- 🔍 Automatic detection of SonarQube/SonarCloud issues
- 🤖 AI-powered code fixes using OpenAI's GPT models
- 🔄 Creates pull requests with fixes
- 🛡️ Safe fix validation to prevent breaking changes
- 🔧 Configurable through environment variables
- 📊 Supports multiple programming languages (Java, Python, JavaScript, etc.)

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Git
- SonarQube/SonarCloud account with API access
- OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Abhishek222747/sonar-fix-agent.git
   cd sonar-fix-agent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables (create a `.env` file):
   ```env
   # Required
   GITHUB_TOKEN=your_github_token
   SONAR_TOKEN=your_sonar_token
   SONAR_URL=https://sonarcloud.io  # or your SonarQube instance
   SONAR_ORGANIZATION=your_org
   SONAR_PROJECT_KEY=your_project_key
   OPENAI_API_KEY=your_openai_api_key
   
   # Optional
   REPOSITORY=owner/repo  # if not provided, will use current repo
   MAX_FIXES_PER_PR=3     # number of fixes per pull request
   ```

## 🛠️ Usage

### Run Locally

```bash
python -m sonar_fix_agent.main
```

### GitHub Actions

Add this workflow to your repository (`.github/workflows/sonar-fix.yml`):

```yaml
name: Sonar Fix Agent

on:
  schedule:
    - cron: '0 0 * * *'  # Run daily
  workflow_dispatch:

jobs:
  sonar-fix:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Run Sonar Fix Agent
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_URL: ${{ secrets.SONAR_URL || 'https://sonarcloud.io' }}
          SONAR_ORGANIZATION: ${{ secrets.SONAR_ORGANIZATION }}
          SONAR_PROJECT_KEY: ${{ secrets.SONAR_PROJECT_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          MAX_FIXES_PER_PR: 3
        run: |
          pip install -r requirements.txt
          python -m sonar_fix_agent.main
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub token with `repo` scope |
| `SONAR_TOKEN` | Yes | SonarQube/SonarCloud token |
| `SONAR_URL` | Yes | SonarQube/SonarCloud URL |
| `SONAR_ORGANIZATION` | Yes | SonarQube organization |
| `SONAR_PROJECT_KEY` | Yes | SonarQube project key |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `REPOSITORY` | No | GitHub repository (owner/repo) |
| `MAX_FIXES_PER_PR` | No | Maximum number of fixes per PR (default: 3) |

## 🤖 How It Works

1. **Analysis**: Fetches issues from SonarQube/SonarCloud
2. **Prioritization**: Selects safe, high-impact issues to fix
3. **Fixing**: Uses AI to generate code fixes
4. **Validation**: Ensures fixes don't break the build
5. **PR Creation**: Creates pull requests with the fixes

## 🛡️ Safety Measures

- Only applies fixes that are verified to be safe
- Runs tests before creating PRs (if test suite exists)
- Limits number of changes per PR for easier review
- Provides detailed explanations of changes

## 📈 Roadmap

- [x] Basic SonarQube/SonarCloud integration
- [x] AI-powered code fixes
- [x] GitHub PR automation
- [ ] Support for more programming languages
- [ ] Custom rule configuration
- [ ] Local testing framework
- [ ] Performance optimizations

## 🙏 Acknowledgments

- [SonarQube](https://www.sonarqube.org/) for the amazing code quality platform
- [OpenAI](https://openai.com/) for the powerful language models
- All contributors who helped improve this project

---

<p align="center">
  Made with ❤️ by Abhishek Kumar
</p>
