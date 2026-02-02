#!/usr/bin/env python3
"""
Instagram crawler for CrossFit WOD Tracker
Anti-blocking best practices applied from scrapingbee.com guide
"""

import os
import sys
import json
import argparse
import time
import random
import socket
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# Force IPv4 connections (fixes issues with some mobile hotspots)
_original_getaddrinfo = socket.getaddrinfo
def _getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _getaddrinfo_ipv4

try:
    import instaloader
except ImportError:
    print("Error: instaloader is not installed.")
    print("Install it with: pip install instaloader")
    sys.exit(1)

# Try to load dotenv for .env file support
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Realistic User-Agent strings (Chrome on various platforms)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.2; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class RateLimiter:
    """Adaptive rate limiter with exponential backoff."""

    def __init__(self, min_delay: float = 3.0, max_delay: float = 7.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.current_delay = min_delay
        self.consecutive_errors = 0
        self.requests_since_error = 0

    def wait(self):
        """Wait with random jitter."""
        # Add random jitter to avoid predictable patterns
        jitter = random.uniform(0.5, 1.5)
        delay = self.current_delay * jitter

        # Occasionally add longer pauses to simulate human behavior
        if random.random() < 0.1:  # 10% chance
            delay += random.uniform(2, 5)
            logger.debug(f"Adding extra pause: {delay:.1f}s")

        time.sleep(delay)
        self.requests_since_error += 1

        # Gradually decrease delay if successful
        if self.requests_since_error > 10 and self.current_delay > self.min_delay:
            self.current_delay = max(self.min_delay, self.current_delay * 0.95)

    def backoff(self):
        """Exponential backoff on error."""
        self.consecutive_errors += 1
        self.requests_since_error = 0

        # Exponential backoff with cap
        backoff_time = min(300, (2 ** self.consecutive_errors) * 10)
        self.current_delay = min(self.max_delay * 2, self.current_delay * 1.5)

        logger.warning(f"Rate limited! Backing off for {backoff_time}s (attempt {self.consecutive_errors})")
        time.sleep(backoff_time)

    def reset_errors(self):
        """Reset error count on success."""
        if self.consecutive_errors > 0:
            logger.info("Connection recovered, resetting error count")
        self.consecutive_errors = 0


# Promotional text to remove from WOD captions
# Note: Instagram may use non-breaking spaces (\xa0), so we include both versions
PROMO_TEXT_TO_REMOVE = [
    "#crossfit #크로스핏 crossfitgangnam  #크로스핏강남 cfgn cfgnej #언주역크로스핏 #크로스핏강남언주 언주역 학동역 역삼역 신논현역 논현로614  025556744",
    "#crossfit #크로스핏 crossfitgangnam\xa0 #크로스핏강남 cfgn cfgnej #언주역크로스핏 #크로스핏강남언주 언주역 학동역 역삼역 신논현역 논현로614\xa0 025556744",
]


class InstagramCrawler:
    """Instagram crawler with anti-blocking features."""

    def __init__(
        self,
        target_username: str,
        output_path: Path,
        login_user: Optional[str] = None,
        login_pass: Optional[str] = None,
        proxy: Optional[str] = None,
        min_delay: float = 3.0,
        max_delay: float = 7.0,
        max_posts: Optional[int] = None,
    ):
        self.target_username = target_username
        self.output_path = output_path
        self.login_user = login_user
        self.login_pass = login_pass
        self.proxy = proxy
        self.max_posts = max_posts
        self.skip_first = 0
        self.stop_on_existing = False
        self.rate_limiter = RateLimiter(min_delay, max_delay)
        self.loader = None
        self.wods: Dict[str, str] = {}
        self.start_time = None
        self.posts_fetched = 0

    def _get_session_file_path(self, username: str) -> Path:
        """Get the path for storing the session file."""
        return Path.home() / ".config" / "instaloader" / f"session-{username}"

    def _create_loader(self) -> instaloader.Instaloader:
        """Create and configure an Instaloader instance with anti-blocking settings."""

        # Select a random user agent
        user_agent = random.choice(USER_AGENTS)
        logger.info(f"Using User-Agent: {user_agent[:50]}...")

        loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            post_metadata_txt_pattern="",
            max_connection_attempts=5,
            request_timeout=60,
            user_agent=user_agent,
        )

        # Configure proxy if provided
        if self.proxy:
            logger.info(f"Using proxy: {self.proxy[:30]}...")
            loader.context._session.proxies = {
                'http': self.proxy,
                'https': self.proxy,
            }

        # Try to load existing session
        if self.login_user:
            session_file = self._get_session_file_path(self.login_user)
            if session_file.exists():
                try:
                    loader.load_session_from_file(self.login_user, str(session_file))
                    logger.info(f"Loaded existing session for {self.login_user}")
                    return loader
                except Exception as e:
                    logger.warning(f"Could not load session: {e}")

            # Login with credentials
            if self.login_pass:
                try:
                    logger.info(f"Logging in as {self.login_user}...")
                    loader.login(self.login_user, self.login_pass)
                    session_file.parent.mkdir(parents=True, exist_ok=True)
                    loader.save_session_to_file(str(session_file))
                    logger.info("Login successful, session saved")
                except instaloader.exceptions.BadCredentialsException:
                    logger.error("Invalid Instagram credentials")
                    sys.exit(1)
                except instaloader.exceptions.TwoFactorAuthRequiredException:
                    logger.error("Two-factor authentication required")
                    sys.exit(1)
                except Exception as e:
                    logger.error(f"Login error: {e}")
                    sys.exit(1)

        return loader

    def _load_existing_wods(self) -> Dict[str, str]:
        """Load existing WODs from file if it exists."""
        if self.output_path.exists():
            try:
                with open(self.output_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load existing WODs: {e}")
        return {}

    def _clean_wod_text(self, text: str) -> str:
        """Clean WOD text by removing promotional hashtags and trimming whitespace."""
        cleaned = text
        for promo in PROMO_TEXT_TO_REMOVE:
            cleaned = cleaned.replace(promo, "")
        return cleaned.strip()

    def _save_wods(self):
        """Save WODs to JSON file."""
        sorted_wods = dict(sorted(self.wods.items(), reverse=True))
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(sorted_wods, f, indent=2, ensure_ascii=False)

    def _get_progress_stats(self) -> str:
        """Get progress statistics."""
        if not self.start_time:
            return ""

        elapsed = time.time() - self.start_time
        if self.posts_fetched > 0:
            rate = self.posts_fetched / (elapsed / 60)  # posts per minute
            return f"[{self.posts_fetched} posts, {rate:.1f}/min, {elapsed/60:.1f}min elapsed]"
        return ""

    def _is_off_peak_hours(self) -> bool:
        """Check if current time is off-peak (after midnight KST)."""
        # KST is UTC+9
        from datetime import timezone, timedelta
        kst = timezone(timedelta(hours=9))
        current_hour = datetime.now(kst).hour
        return 0 <= current_hour <= 6

    def run(self) -> Dict[str, str]:
        """Run the crawler with anti-blocking measures."""

        self.start_time = time.time()

        # Check if off-peak hours
        if self.is_off_peak_hours():
            logger.info("Running during off-peak hours (KST) - optimal for scraping")
        else:
            logger.warning("Consider running during off-peak hours (00:00-06:00 KST) for better success rate")

        # Load existing WODs
        self.wods = self._load_existing_wods()
        existing_dates = set(self.wods.keys())

        if existing_dates:
            logger.info(f"Loaded {len(existing_dates)} existing WODs, will skip duplicates")

        # Create loader with anti-blocking settings
        self.loader = self._create_loader()

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                self._fetch_posts(existing_dates)
                break  # Success
            except (instaloader.exceptions.QueryReturnedBadRequestException,
                    instaloader.exceptions.ConnectionException) as e:
                retry_count += 1
                logger.warning(f"Connection error (attempt {retry_count}/{max_retries}): {e}")

                if retry_count < max_retries:
                    self.rate_limiter.backoff()
                    # Rotate user agent on retry
                    self.loader = self._create_loader()
                else:
                    logger.error("Max retries reached. Saving progress and exiting.")
                    self._save_wods()
                    sys.exit(1)
            except KeyboardInterrupt:
                logger.info("Interrupted by user. Saving progress...")
                self._save_wods()
                logger.info(f"Saved {len(self.wods)} WODs")
                sys.exit(0)
            except Exception as e:
                error_msg = str(e).lower()
                if "wait a few minutes" in error_msg or "401" in error_msg or "429" in error_msg or "403" in error_msg:
                    retry_count += 1
                    if retry_count < max_retries:
                        self.rate_limiter.backoff()
                        self.loader = self._create_loader()
                    else:
                        logger.error("Rate limited. Saving progress...")
                        self._save_wods()
                        logger.info(f"Saved {len(self.wods)} WODs. Try again later.")
                        sys.exit(1)
                else:
                    logger.error(f"Unexpected error: {e}")
                    self._save_wods()
                    sys.exit(1)

        # Final save
        self._save_wods()
        logger.info(f"Completed! Saved {len(self.wods)} WODs to {self.output_path}")

        return self.wods

    def is_off_peak_hours(self) -> bool:
        """Check if current time is off-peak hours in KST."""
        try:
            from datetime import timezone, timedelta
            kst = timezone(timedelta(hours=9))
            current_hour = datetime.now(kst).hour
            return 0 <= current_hour <= 6
        except Exception:
            return False

    def _fetch_posts(self, existing_dates: set):
        """Fetch posts with rate limiting and progress tracking."""

        logger.info(f"Fetching profile: {self.target_username}")

        # Initial delay before starting
        logger.info("Starting with initial delay...")
        time.sleep(random.uniform(2, 5))

        profile = instaloader.Profile.from_username(self.loader.context, self.target_username)
        post_count = profile.mediacount
        logger.info(f"Found {post_count} posts")

        if self.max_posts:
            logger.info(f"Limiting to {self.max_posts} posts")

        new_count = 0
        skipped_count = 0

        for i, post in enumerate(profile.get_posts(), 1):
            # Skip first N posts without API calls (for resuming)
            if self.skip_first and i <= self.skip_first:
                if i % 50 == 0 or i == self.skip_first:
                    logger.info(f"[{i}/{post_count}] Skipping (fast-forward to post {self.skip_first})...")
                continue

            if self.max_posts and (i - self.skip_first) > self.max_posts:
                logger.info(f"Reached max posts limit ({self.max_posts})")
                break

            # Get post date
            post_date = post.date_local.strftime("%Y-%m-%d")

            # Get caption
            caption = post.caption or ""

            # Skip posts without captions
            if not caption.strip():
                logger.debug(f"[{i}/{post_count}] {post_date} - Skipped (no caption)")
                skipped_count += 1
                continue

            # Check if already exists
            base_date = post_date
            if base_date in existing_dates:
                if self.stop_on_existing:
                    logger.info(f"[{i}/{post_count}] {post_date} - Already exists, stopping (--stop-on-existing)")
                    break
                else:
                    logger.info(f"[{i}/{post_count}] {post_date} - Already exists, skipping")
                    skipped_count += 1
                    self.rate_limiter.wait()
                    continue

            # Handle multiple posts on same day
            if post_date in self.wods:
                idx = 2
                while f"{post_date}-{idx}" in self.wods:
                    idx += 1
                post_date = f"{post_date}-{idx}"

            self.wods[post_date] = self._clean_wod_text(caption)
            new_count += 1
            self.posts_fetched += 1

            stats = self._get_progress_stats()
            logger.info(f"[{i}/{post_count}] {post_date} - Saved (new: {new_count}) {stats}")

            # Reset error count on successful fetch
            self.rate_limiter.reset_errors()

            # Checkpoint save every 10 new posts
            if new_count % 10 == 0:
                self._save_wods()
                logger.info(f"[Checkpoint] Saved {len(self.wods)} WODs")

            # Rate limiting with random delay
            self.rate_limiter.wait()


def main():
    parser = argparse.ArgumentParser(
        description="Instagram WOD Crawler with Anti-Blocking Features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (anonymous, slower)
  python crawl_instagram.py

  # With login (faster, more reliable)
  python crawl_instagram.py --login-user myuser --login-pass mypass

  # With proxy
  python crawl_instagram.py --proxy http://user:pass@proxy:port

  # Limit posts and custom delay
  python crawl_instagram.py --max-posts 100 --delay-min 5 --delay-max 10

Environment Variables:
  INSTAGRAM_USER     - Instagram username for login
  INSTAGRAM_PASS     - Instagram password for login
  PROXY_HTTP         - HTTP proxy URL
  MIN_DELAY          - Minimum delay between requests (default: 3)
  MAX_DELAY          - Maximum delay between requests (default: 7)
        """
    )

    parser.add_argument(
        "--username", "-u",
        default="cfgn_ej",
        help="Instagram username to crawl (default: cfgn_ej)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path (default: src/data/wods.json)"
    )
    parser.add_argument(
        "--login-user",
        default=None,
        help="Instagram username for login"
    )
    parser.add_argument(
        "--login-pass",
        default=None,
        help="Instagram password for login"
    )
    parser.add_argument(
        "--proxy",
        default=None,
        help="Proxy URL (e.g., http://user:pass@host:port)"
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=None,
        help="Minimum delay between requests (default: 3.0)"
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=None,
        help="Maximum delay between requests (default: 7.0)"
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=None,
        help="Maximum number of posts to fetch"
    )
    parser.add_argument(
        "--skip-first",
        type=int,
        default=0,
        help="Skip first N posts without API calls (for resuming from a specific point)"
    )
    parser.add_argument(
        "--stop-on-existing",
        action="store_true",
        help="Stop crawling when an existing post is found (efficient for daily updates)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        script_dir = Path(__file__).parent
        output_path = script_dir.parent / "src" / "data" / "wods.json"

    # Get settings from args or environment
    login_user = args.login_user or os.environ.get("INSTAGRAM_USER")
    login_pass = args.login_pass or os.environ.get("INSTAGRAM_PASS")
    proxy = args.proxy or os.environ.get("PROXY_HTTP") or os.environ.get("PROXY_HTTPS")
    min_delay = args.delay_min or float(os.environ.get("MIN_DELAY", "3.0"))
    max_delay = args.delay_max or float(os.environ.get("MAX_DELAY", "7.0"))

    # Print configuration
    print("=" * 60)
    print("CrossFit WOD Instagram Crawler (Anti-Blocking Edition)")
    print("=" * 60)
    print(f"Target account: {args.username}")
    print(f"Output file: {output_path}")
    print(f"Login: {login_user if login_user else 'Anonymous (limited access)'}")
    print(f"Proxy: {proxy[:30] + '...' if proxy and len(proxy) > 30 else proxy or 'None'}")
    print(f"Delay: {min_delay}-{max_delay}s (with random jitter)")
    print(f"Max posts: {args.max_posts or 'All'}")
    print(f"Skip first: {args.skip_first or 0} posts")
    print(f"Stop on existing: {args.stop_on_existing}")
    print("=" * 60)
    print()

    # Create and run crawler
    crawler = InstagramCrawler(
        target_username=args.username,
        output_path=output_path,
        login_user=login_user,
        login_pass=login_pass,
        proxy=proxy,
        min_delay=min_delay,
        max_delay=max_delay,
        max_posts=args.max_posts,
    )
    crawler.skip_first = args.skip_first
    crawler.stop_on_existing = args.stop_on_existing

    crawler.run()


if __name__ == "__main__":
    main()
