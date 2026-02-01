# Instagram Crawler Scripts

This directory contains scripts for crawling Instagram posts to populate the WOD data.
Anti-blocking best practices applied based on [ScrapingBee's guide](https://www.scrapingbee.com/blog/web-scraping-without-getting-blocked/).

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

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp scripts/.env.example scripts/.env
```

Available settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `INSTAGRAM_USER` | Instagram username for login | None |
| `INSTAGRAM_PASS` | Instagram password for login | None |
| `PROXY_HTTP` | HTTP proxy URL | None |
| `MIN_DELAY` | Minimum delay between requests | 3.0 |
| `MAX_DELAY` | Maximum delay between requests | 7.0 |

## Usage

### Basic Usage

```bash
# Activate virtual environment
source scripts/venv/bin/activate

# Run crawler
python scripts/crawl_instagram.py
```

### With Custom Options

```bash
# Limit to 100 posts with slower delays
python scripts/crawl_instagram.py --max-posts 100 --delay-min 5 --delay-max 10

# With proxy
python scripts/crawl_instagram.py --proxy http://user:pass@proxy:port

# With login
python scripts/crawl_instagram.py --login-user myuser --login-pass mypass

# Debug mode (verbose output)
python scripts/crawl_instagram.py --debug
```

## Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--username` | `-u` | Instagram account to crawl | `cfgn_ej` |
| `--output` | `-o` | Output JSON file path | `src/data/wods.json` |
| `--login-user` | | Your Instagram username | `INSTAGRAM_USER` env |
| `--login-pass` | | Your Instagram password | `INSTAGRAM_PASS` env |
| `--proxy` | | Proxy URL | `PROXY_HTTP` env |
| `--delay-min` | | Minimum delay (seconds) | 3.0 |
| `--delay-max` | | Maximum delay (seconds) | 7.0 |
| `--max-posts` | | Maximum posts to fetch | All |
| `--debug` | | Enable debug logging | Off |

## Anti-Blocking Features

This crawler implements several techniques to avoid getting blocked:

### 1. Request Rate Limiting
- Random delays between 3-7 seconds (configurable)
- Random jitter added to avoid predictable patterns
- 10% chance of additional 2-5 second pause to simulate human behavior

### 2. Exponential Backoff
- Automatically backs off on rate limiting errors
- Doubles wait time on each consecutive error (capped at 5 minutes)
- Resets after successful requests

### 3. User-Agent Rotation
- Uses realistic, up-to-date browser user agents
- Rotates randomly from Chrome, Firefox, Safari on various platforms
- Changes user agent on retry after errors

### 4. Proxy Support
- Optional proxy configuration via command line or environment variable
- Residential proxies recommended for better success rates

### 5. Session Persistence
- Saves login session to avoid repeated logins
- Sessions stored in `~/.config/instaloader/session-{username}`

### 6. Progress Checkpoints
- Saves progress every 10 new posts
- Can resume from where it left off on restart

## Best Practices for Avoiding Blocks

### Recommended Scraping Times
Run the crawler during off-peak hours for better success rates:
- **00:00 - 06:00 KST** (Korean Standard Time)
- **15:00 - 21:00 UTC**

The crawler will log a warning if running outside these hours.

### Delay Settings
- **Conservative (recommended)**: `--delay-min 5 --delay-max 10`
- **Default**: `--delay-min 3 --delay-max 7`
- **Aggressive (higher risk)**: `--delay-min 1 --delay-max 3`

### Using Proxies
Residential proxies are more effective than datacenter proxies:
- [BrightData](https://brightdata.com/)
- [Oxylabs](https://oxylabs.io/)
- [SmartProxy](https://smartproxy.com/)

```bash
export PROXY_HTTP="http://user:pass@proxy.example.com:8080"
python scripts/crawl_instagram.py
```

### Rotating IP Addresses
If you get blocked:
1. Wait 10-30 minutes before retrying
2. Switch to a different network (VPN, mobile hotspot)
3. Use a different VPN server location

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

### Rate Limiting (403/401/429 Errors)

```
Rate limited by Instagram. Saving progress...
```

Solutions:
1. Wait 10-30 minutes before retrying
2. Switch network (VPN, mobile hotspot, different Wi-Fi)
3. Use a proxy server
4. Run during off-peak hours (00:00-06:00 KST)

### "Profile is private"

Login with an account that follows the private profile:

```bash
python scripts/crawl_instagram.py --login-user your_username --login-pass your_password
```

### "Two-factor authentication required"

Options:
1. Temporarily disable 2FA, login once (session saved), then re-enable
2. Use a dedicated scraping account without 2FA

### Session Expired

```bash
# Remove old session and login again
rm ~/.config/instaloader/session-*
python scripts/crawl_instagram.py --login-user your_username --login-pass your_password
```

### IPv6 Connection Issues (Mobile Hotspot)

The script automatically forces IPv4 connections to fix issues with some mobile hotspots.

## Security Notes

- Never commit credentials to version control
- Use environment variables for sensitive data
- Keep session files secure (`~/.config/instaloader/`)
- Consider using a dedicated Instagram account for scraping
- `.env` file should be in `.gitignore`
