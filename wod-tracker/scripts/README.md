# Instagram Crawler Scripts

This directory contains scripts for crawling Instagram posts to populate the WOD data.

## Setup

### Option 1: Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv scripts/venv

# Activate it
source scripts/venv/bin/activate

# Install dependencies
pip install -r scripts/requirements.txt
```

### Option 2: Using pipx

```bash
brew install pipx
pipx install instaloader
```

### Option 3: Direct pip install

```bash
pip install instaloader
# or
pip3 install instaloader
```

## Usage

### Basic Usage (Public Profiles)

```bash
# If using virtual environment, activate it first
source scripts/venv/bin/activate

python3 scripts/crawl_instagram.py
```

This will crawl the default account (`cfgn_ej`) and save posts to `src/data/wods.json`.

### Custom Target Account

```bash
python3 scripts/crawl_instagram.py --username some_crossfit_box
```

### Custom Output File

```bash
python3 scripts/crawl_instagram.py --output /path/to/output.json
```

### Private Profiles (Requires Login)

For private profiles, you need to login with an Instagram account that follows the target profile.

**Option 1: Environment Variables (Recommended)**

```bash
export INSTAGRAM_USER="your_username"
export INSTAGRAM_PASS="your_password"
python3 scripts/crawl_instagram.py
```

**Option 2: Command Line Arguments**

```bash
python3 scripts/crawl_instagram.py --login-user your_username --login-pass your_password
```

Note: The script will save your session to `~/.config/instaloader/session-{username}` so you don't need to login every time.

## Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--username` | `-u` | Instagram account to crawl | `cfgn_ej` |
| `--output` | `-o` | Output JSON file path | `src/data/wods.json` |
| `--login-user` | | Your Instagram username | `INSTAGRAM_USER` env var |
| `--login-pass` | | Your Instagram password | `INSTAGRAM_PASS` env var |

## Output Format

The script generates a JSON file with the following structure:

```json
{
  "2024-01-29": "For Time: 21-15-9 Thrusters (95/65) Pull-ups",
  "2024-01-28": "AMRAP 20: 5 Power Cleans...",
  ...
}
```

Posts are sorted by date in descending order (newest first).

## Troubleshooting

### "Profile is private"

You need to login with an account that follows the private profile:

```bash
export INSTAGRAM_USER="your_username"
export INSTAGRAM_PASS="your_password"
python3 scripts/crawl_instagram.py
```

### "Login required"

Instagram may require login to access some profiles. Use the login options above.

### "Two-factor authentication required"

If your account has 2FA enabled, you have two options:

1. Temporarily disable 2FA, login once (session will be saved), then re-enable 2FA
2. Use a browser to login and export the session manually

### Rate Limiting

Instagram may rate-limit requests. If you encounter issues:

- Wait a few minutes and try again
- Use a logged-in session (sessions have higher rate limits)
- Avoid running the script too frequently

### Session Expired

If you get authentication errors after previously successful logins:

```bash
# Remove old session and login again
rm ~/.config/instaloader/session-*
python3 scripts/crawl_instagram.py --login-user your_username --login-pass your_password
```

## Security Notes

- Never commit credentials to version control
- Use environment variables for sensitive data
- The saved session file contains authentication tokens - keep it secure
- Consider using a dedicated Instagram account for scraping
