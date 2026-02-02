#!/usr/bin/env python3
"""
Instagram Web Scraper for CrossFit WOD Tracker
Uses Playwright headless browser to scrape Instagram public profiles
"""

import json
import re
import time
import random
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

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

    def __init__(self, username: str, output_path: Path):
        self.username = username
        self.output_path = output_path
        self.wods: Dict[str, str] = {}

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

    def run(self, stop_on_existing: bool = False) -> Dict[str, str]:
        """Run the Playwright scraper."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return {}

        logger.info(f"Starting Playwright scraper for @{self.username}")

        # Load existing WODs
        self.wods = self._load_existing_wods()
        existing_dates = set(self.wods.keys())
        logger.info(f"Loaded {len(existing_dates)} existing WODs")

        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()

            try:
                # Navigate to profile
                url = f"https://www.instagram.com/{self.username}/"
                logger.info(f"Navigating to {url}")
                page.goto(url, wait_until='networkidle', timeout=60000)

                # Wait for posts to load
                time.sleep(3)

                # Try to find and click on posts
                posts_data = []

                # Find all post links
                post_links = page.query_selector_all('a[href*="/p/"]')
                logger.info(f"Found {len(post_links)} post links")

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
                        page.goto(post_url, wait_until='networkidle', timeout=30000)
                        time.sleep(random.uniform(1, 2))

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
            finally:
                browser.close()

        return self.wods


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

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

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
    print("=" * 60)

    scraper = InstagramPlaywrightScraper(args.username, output_path)
    scraper.run(stop_on_existing=args.stop_on_existing)


if __name__ == "__main__":
    main()
