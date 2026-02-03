#!/usr/bin/env python3
"""
Instagram Web Scraper for CrossFit WOD Tracker
Uses Playwright headless browser to scrape Instagram public profiles
"""

import json
import os
import re
import sys
import time
import random
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Promotional text to remove from WOD captions
PROMO_TEXT_TO_REMOVE = [
    "#crossfit #크로스핏 crossfitgangnam  #크로스핏강남 cfgn cfgnej #언주역크로스핏 #크로스핏강남언주 언주역 학동역 역삼역 신논현역 논현로614  025556744",
    "#crossfit #크로스핏 crossfitgangnam\xa0 #크로스핏강남 cfgn cfgnej #언주역크로스핏 #크로스핏강남언주 언주역 학동역 역삼역 신논현역 논현로614\xa0 025556744",
]


class InstagramPlaywrightScraper:
    """Scraper using Playwright headless browser."""

    def __init__(self, username: str, output_path: Path, login_user: str = None, login_pass: str = None, session_data: str = None):
        self.username = username
        self.output_path = output_path
        self.wods: Dict[str, str] = {}
        self.login_user = login_user
        self.login_pass = login_pass
        self.session_data = session_data  # JSON string of storage state

    def _clean_wod_text(self, text: str) -> str:
        """Clean WOD text by removing promotional hashtags and metadata."""
        cleaned = text

        # Remove Instagram meta description prefix
        # Pattern: "XX likes, XX comments - username on DATE: "CONTENT"."
        meta_pattern = r'^\d+\s*likes?,?\s*\d*\s*comments?\s*-\s*\w+\s+on\s+[^:]+:\s*"?'
        cleaned = re.sub(meta_pattern, '', cleaned, flags=re.IGNORECASE)

        # Remove trailing quote and period from meta description
        cleaned = re.sub(r'"\.?\s*$', '', cleaned)

        # Remove promotional text
        for promo in PROMO_TEXT_TO_REMOVE:
            cleaned = cleaned.replace(promo, "")

        return cleaned.strip()

    def _load_existing_wods(self) -> Dict[str, str]:
        """Load existing WODs from file if it exists."""
        if self.output_path.exists():
            try:
                with open(self.output_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load existing WODs: {e}")
        return {}

    def _save_wods(self):
        """Save WODs to JSON file."""
        sorted_wods = dict(sorted(self.wods.items(), reverse=True))
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(sorted_wods, f, indent=2, ensure_ascii=False)

    def _extract_date_from_text(self, text: str) -> Optional[str]:
        """Try to extract date from WOD text (e.g., '20260203 W.O.D!!')."""
        # Pattern: 8 digits at the start that look like YYYYMMDD
        match = re.search(r'(\d{8})\s*W\.?O\.?D', text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            try:
                # Parse YYYYMMDD format
                dt = datetime.strptime(date_str, "%Y%m%d")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return None

    def _login(self, page) -> bool:
        """Login to Instagram."""
        if not self.login_user or not self.login_pass:
            logger.warning("No login credentials provided")
            return False

        try:
            logger.info("Attempting to login to Instagram...")
            page.goto("https://www.instagram.com/accounts/login/", wait_until='domcontentloaded', timeout=60000)

            # Wait for page to fully render
            time.sleep(5)

            # Handle cookie consent first - try multiple times
            for attempt in range(3):
                try:
                    cookie_buttons = [
                        'button:has-text("Allow all cookies")',
                        'button:has-text("Allow essential and optional cookies")',
                        'button:has-text("Accept All")',
                        'button:has-text("Accept")',
                        'button:has-text("허용")',
                        'button:has-text("Decline optional cookies")',
                    ]
                    clicked = False
                    for selector in cookie_buttons:
                        btn = page.query_selector(selector)
                        if btn and btn.is_visible():
                            btn.click()
                            logger.info(f"Clicked cookie consent button: {selector}")
                            time.sleep(2)
                            clicked = True
                            break
                    if clicked:
                        break
                except Exception as e:
                    logger.debug(f"Cookie popup attempt {attempt + 1}: {e}")
                time.sleep(1)

            # Save screenshot for debugging
            login_screenshot = self.output_path.parent / "debug_login.png"
            page.screenshot(path=str(login_screenshot))
            logger.info(f"Saved login page screenshot to {login_screenshot}")

            # Wait for login form to appear
            logger.info("Waiting for login form...")
            try:
                page.wait_for_selector('input[name="username"], input[type="text"]', timeout=10000)
            except Exception as e:
                logger.warning(f"Timeout waiting for login form: {e}")

            # Try multiple selectors for username input
            username_selectors = [
                'input[name="username"]',
                'input[aria-label="Phone number, username, or email"]',
                'input[aria-label*="username"]',
                'input[autocomplete="username"]',
                'form input[type="text"]',
            ]
            username_input = None
            for selector in username_selectors:
                try:
                    username_input = page.query_selector(selector)
                    if username_input and username_input.is_visible():
                        logger.info(f"Found username input with selector: {selector}")
                        break
                    username_input = None
                except Exception:
                    pass

            # Try multiple selectors for password input
            password_selectors = [
                'input[name="password"]',
                'input[aria-label="Password"]',
                'input[autocomplete="current-password"]',
                'input[type="password"]',
            ]
            password_input = None
            for selector in password_selectors:
                try:
                    password_input = page.query_selector(selector)
                    if password_input and password_input.is_visible():
                        logger.info(f"Found password input with selector: {selector}")
                        break
                    password_input = None
                except Exception:
                    pass

            if username_input and password_input:
                username_input.fill(self.login_user)
                time.sleep(0.5)
                password_input.fill(self.login_pass)
                time.sleep(0.5)

                # Click login button
                login_btn_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Log in")',
                    'button:has-text("Log In")',
                    'div[role="button"]:has-text("Log in")',
                ]
                login_btn = None
                for selector in login_btn_selectors:
                    login_btn = page.query_selector(selector)
                    if login_btn:
                        break

                if login_btn:
                    login_btn.click()
                    logger.info("Clicked login button")
                    time.sleep(8)  # Wait longer for login to complete

                    # Log current URL for debugging
                    current_url = page.url
                    logger.info(f"Current URL after login: {current_url}")

                    # Save screenshot after login attempt
                    page.screenshot(path=str(self.output_path.parent / "debug_after_login.png"))

                    # Handle "Save Login Info" popup (this appears when login is successful)
                    try:
                        save_info_selectors = [
                            'button:has-text("Not now")',
                            'button:has-text("Not Now")',
                            'div[role="button"]:has-text("Not now")',
                            'div[role="button"]:has-text("Not Now")',
                            'button:has-text("Save info")',  # Also try clicking save
                        ]
                        for selector in save_info_selectors:
                            not_now_btn = page.query_selector(selector)
                            if not_now_btn and not_now_btn.is_visible():
                                not_now_btn.click()
                                logger.info(f"Clicked '{selector}' on save login info popup")
                                time.sleep(2)
                                break
                    except Exception as e:
                        logger.debug(f"No save login info popup: {e}")

                    # Handle notifications popup
                    try:
                        time.sleep(1)
                        for selector in save_info_selectors:
                            not_now_btn = page.query_selector(selector)
                            if not_now_btn and not_now_btn.is_visible():
                                not_now_btn.click()
                                logger.info("Clicked 'Not now' on notifications popup")
                                time.sleep(1)
                                break
                    except Exception:
                        pass

                    # Update URL after handling popups
                    current_url = page.url
                    logger.info(f"Final URL: {current_url}")

                    # Check if login was successful by looking for home page elements
                    home_indicators = [
                        'svg[aria-label="Home"]',
                        'svg[aria-label="홈"]',
                        'a[href="/"]',
                        'nav',
                        'a[href*="/direct/"]',
                    ]
                    for indicator in home_indicators:
                        elem = page.query_selector(indicator)
                        if elem:
                            logger.info(f"Login successful! Found indicator: {indicator}")
                            return True

                    # Check URL - if not on login/challenge page, consider success
                    if "/accounts/login" not in current_url and "/challenge" not in current_url:
                        logger.info("Login successful (URL check)!")
                        return True

                    # If we're on a challenge page, log it
                    if "/challenge" in current_url:
                        logger.error("Instagram requires additional verification (challenge)")
                        page.screenshot(path=str(self.output_path.parent / "debug_challenge.png"))
                        return False

                    logger.error(f"Login failed - could not verify success. URL: {current_url}")
                    page.screenshot(path=str(self.output_path.parent / "debug_login_failed.png"))
                    return False
            else:
                logger.error(f"Could not find login form inputs (username: {username_input is not None}, password: {password_input is not None})")
                return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

        return False

    def run(self, stop_on_existing: bool = False) -> Tuple[Dict[str, str], bool]:
        """Run the Playwright scraper.

        Returns:
            Tuple of (wods dict, success bool). Success is False if no posts were found.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return {}, False

        logger.info(f"Starting Playwright scraper for @{self.username}")

        # Load existing WODs
        self.wods = self._load_existing_wods()
        existing_dates = set(self.wods.keys())
        logger.info(f"Loaded {len(existing_dates)} existing WODs")

        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)

            # Prepare context options
            context_options = {
                'viewport': {'width': 1280, 'height': 720},
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            # Use session data if available
            if self.session_data:
                try:
                    storage_state = json.loads(self.session_data)
                    context_options['storage_state'] = storage_state
                    logger.info("Using saved session data")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid session data: {e}")

            context = browser.new_context(**context_options)
            page = context.new_page()

            try:
                # Login if session not provided and credentials available
                if not self.session_data and self.login_user and self.login_pass:
                    if not self._login(page):
                        logger.error("Failed to login, continuing without authentication")

                # Navigate to profile
                url = f"https://www.instagram.com/{self.username}/"
                logger.info(f"Navigating to {url}")
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                # Wait for content to load
                time.sleep(3)

                # Wait for initial load
                time.sleep(2)

                # Handle cookie consent popup
                try:
                    cookie_buttons = [
                        'button:has-text("Allow all cookies")',
                        'button:has-text("Accept All")',
                        'button:has-text("Accept")',
                        '[data-testid="cookie-policy-manage-dialog-accept-button"]',
                    ]
                    for selector in cookie_buttons:
                        btn = page.query_selector(selector)
                        if btn:
                            btn.click()
                            logger.info("Clicked cookie consent button")
                            time.sleep(1)
                            break
                except Exception as e:
                    logger.debug(f"No cookie popup or error: {e}")

                # Handle login popup (click outside or close button)
                try:
                    login_close_selectors = [
                        '[aria-label="Close"]',
                        'svg[aria-label="Close"]',
                        'button:has-text("Not Now")',
                        'button:has-text("Not now")',
                    ]
                    for selector in login_close_selectors:
                        btn = page.query_selector(selector)
                        if btn:
                            btn.click()
                            logger.info("Closed login popup")
                            time.sleep(1)
                            break
                except Exception as e:
                    logger.debug(f"No login popup or error: {e}")

                # Scroll down to trigger lazy loading
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(2)
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(1)

                # Try multiple selectors to find post links
                post_links = []
                post_selectors = [
                    'a[href*="/p/"]',
                    'article a[href*="/p/"]',
                    'main a[href*="/p/"]',
                    'div[style*="flex"] a[href*="/p/"]',
                ]

                for selector in post_selectors:
                    post_links = page.query_selector_all(selector)
                    if post_links:
                        logger.info(f"Found {len(post_links)} post links using selector: {selector}")
                        break

                if not post_links:
                    logger.error("No post links found with any selector")
                    # Save screenshot for debugging
                    screenshot_path = self.output_path.parent / "debug_screenshot.png"
                    page.screenshot(path=str(screenshot_path))
                    logger.info(f"Saved debug screenshot to {screenshot_path}")
                    # Also save page content for debugging
                    html_path = self.output_path.parent / "debug_page.html"
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(page.content())
                    logger.info(f"Saved page HTML to {html_path}")
                    browser.close()
                    return self.wods, False  # Failed to find posts

                # Get unique post URLs
                post_urls = []
                seen = set()
                for link in post_links[:12]:  # Limit to first 12 posts
                    href = link.get_attribute('href')
                    if href and '/p/' in href and href not in seen:
                        seen.add(href)
                        full_url = f"https://www.instagram.com{href}" if href.startswith('/') else href
                        post_urls.append(full_url)

                logger.info(f"Will process {len(post_urls)} unique posts")

                # Visit each post to get caption
                new_count = 0
                for i, post_url in enumerate(post_urls, 1):
                    try:
                        logger.info(f"[{i}/{len(post_urls)}] Fetching: {post_url}")
                        page.goto(post_url, wait_until='domcontentloaded', timeout=30000)
                        time.sleep(random.uniform(2, 3))

                        # Try to find caption
                        caption = ""

                        # Method 1: Look for meta description
                        meta = page.query_selector('meta[property="og:description"]')
                        if meta:
                            caption = meta.get_attribute('content') or ""

                        # Method 2: Look for caption in the page
                        if not caption:
                            # Try to find the caption element
                            caption_selectors = [
                                'div[class*="Caption"] span',
                                'h1 + span',
                                'article span[class*="x193iq5w"]',
                            ]
                            for selector in caption_selectors:
                                elem = page.query_selector(selector)
                                if elem:
                                    caption = elem.inner_text()
                                    if caption and len(caption) > 20:
                                        break

                        if not caption:
                            logger.warning(f"Could not extract caption from {post_url}")
                            continue

                        # Try to extract date from caption
                        post_date = self._extract_date_from_text(caption)
                        if not post_date:
                            # Use current date as fallback
                            post_date = datetime.now().strftime("%Y-%m-%d")
                            logger.warning(f"Could not extract date, using today: {post_date}")

                        # Check if already exists
                        if post_date in existing_dates:
                            if stop_on_existing:
                                logger.info(f"{post_date} - Already exists, stopping")
                                break
                            logger.info(f"{post_date} - Already exists, skipping")
                            continue

                        # Handle multiple posts on same day
                        final_date = post_date
                        if post_date in self.wods:
                            idx = 2
                            while f"{post_date}-{idx}" in self.wods:
                                idx += 1
                            final_date = f"{post_date}-{idx}"

                        # Save cleaned WOD
                        cleaned_caption = self._clean_wod_text(caption)
                        self.wods[final_date] = cleaned_caption
                        new_count += 1
                        logger.info(f"{final_date} - Saved new WOD")

                    except Exception as e:
                        logger.error(f"Error processing {post_url}: {e}")
                        continue

                # Save results
                if new_count > 0:
                    self._save_wods()
                    logger.info(f"Saved {new_count} new WODs (total: {len(self.wods)})")
                else:
                    logger.info("No new WODs found")

            except Exception as e:
                logger.error(f"Scraping error: {e}")
                return self.wods, False
            finally:
                browser.close()

        return self.wods, True


def save_session(login_user: str, login_pass: str, output_file: str):
    """Login and save session to a file."""
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("Instagram Session Saver")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Show browser for manual verification
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        print(f"Logging in as {login_user}...")
        page.goto("https://www.instagram.com/accounts/login/", wait_until='domcontentloaded')
        time.sleep(3)

        # Handle cookie consent
        try:
            for selector in ['button:has-text("Allow all cookies")', 'button:has-text("Accept")']:
                btn = page.query_selector(selector)
                if btn:
                    btn.click()
                    time.sleep(2)
                    break
        except Exception:
            pass

        # Fill login form
        page.fill('input[name="username"]', login_user)
        time.sleep(0.5)
        page.fill('input[name="password"]', login_pass)
        time.sleep(0.5)
        page.click('button[type="submit"]')

        print("Please complete any verification (2FA, code entry) in the browser...")
        print("Press Enter when you're logged in and see the Instagram home page...")
        input()

        # Save session
        storage_state = context.storage_state()
        with open(output_file, 'w') as f:
            json.dump(storage_state, f)

        print(f"Session saved to {output_file}")
        print("")
        print("To use this session in GitHub Actions:")
        print("1. Copy the contents of the session file")
        print("2. Create a GitHub Secret named INSTAGRAM_SESSION")
        print("3. Paste the session JSON as the secret value")

        browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Instagram Playwright Scraper for WOD Tracker"
    )
    parser.add_argument(
        "--username", "-u",
        default="cfgn_ej",
        help="Instagram username to scrape (default: cfgn_ej)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path (default: src/data/wods.json)"
    )
    parser.add_argument(
        "--stop-on-existing",
        action="store_true",
        help="Stop when an existing post is found"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--login-user",
        default=None,
        help="Instagram login username (or set INSTAGRAM_USER env var)"
    )
    parser.add_argument(
        "--login-pass",
        default=None,
        help="Instagram login password (or set INSTAGRAM_PASS env var)"
    )
    parser.add_argument(
        "--save-session",
        default=None,
        metavar="FILE",
        help="Login and save session to file (for later use with --session or INSTAGRAM_SESSION)"
    )
    parser.add_argument(
        "--session",
        default=None,
        metavar="FILE",
        help="Load session from file (or set INSTAGRAM_SESSION env var with JSON content)"
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle session saving mode
    if args.save_session:
        login_user = args.login_user or os.environ.get("INSTAGRAM_USER")
        login_pass = args.login_pass or os.environ.get("INSTAGRAM_PASS")
        if not login_user or not login_pass:
            print("Error: --login-user and --login-pass required for --save-session")
            sys.exit(1)
        save_session(login_user, login_pass, args.save_session)
        return

    # Get login credentials from args or environment variables
    login_user = args.login_user or os.environ.get("INSTAGRAM_USER")
    login_pass = args.login_pass or os.environ.get("INSTAGRAM_PASS")

    # Get session data from file or environment variable
    session_data = None
    if args.session:
        with open(args.session, 'r') as f:
            session_data = f.read()
    elif os.environ.get("INSTAGRAM_SESSION"):
        session_data = os.environ.get("INSTAGRAM_SESSION")

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        script_dir = Path(__file__).parent
        output_path = script_dir.parent / "src" / "data" / "wods.json"

    print("=" * 60)
    print("Instagram Playwright Scraper for WOD Tracker")
    print("=" * 60)
    print(f"Target account: @{args.username}")
    print(f"Output file: {output_path}")
    print(f"Stop on existing: {args.stop_on_existing}")
    print(f"Login user: {login_user or 'Not provided'}")
    print(f"Session: {'Provided' if session_data else 'Not provided'}")
    print("=" * 60)

    scraper = InstagramPlaywrightScraper(args.username, output_path, login_user, login_pass, session_data)
    _, success = scraper.run(stop_on_existing=args.stop_on_existing)

    if not success:
        logger.error("Scraper failed to find posts")
        sys.exit(1)


if __name__ == "__main__":
    main()
