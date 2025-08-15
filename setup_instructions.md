# Setup Instructions

## 1. API Keys Setup

After cloning this repository, you need to set up your API keys:

### Method 1: Edit config.py directly
```bash
# Edit config.py and replace the placeholder values:
CLAUDE_API_KEY = "your-actual-claude-api-key"
OPENAI_API_KEY = "your-actual-openai-api-key"
```

### Method 2: Use environment variables (recommended)
Add to your `.bashrc`, `.zshrc`, or create a `.env` file:
```bash
export CLAUDE_API_KEY="your-actual-claude-api-key"
export OPENAI_API_KEY="your-actual-openai-api-key"
```

## 2. Install Dependencies
```bash
pip install -r requirements.txt
```

## 3. Create Input Directory
```bash
mkdir -p input_videos
# Place your Korean video files here
```

## 4. Run the Program
```bash
python main.py
```

## Security Notes
- ⚠️ **NEVER commit real API keys to Git**
- The `.gitignore` file is configured to prevent accidental commits
- Always use placeholder values in `config.py` for version control