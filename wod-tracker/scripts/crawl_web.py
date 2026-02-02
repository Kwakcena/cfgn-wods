#!/usr/bin/env python3
"""
Instagram Web Scraper for CrossFit WOD Tracker
Uses web scraping instead of Instagram API to avoid rate limiting
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
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

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

# User agents for web scraping
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.2; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class InstagramWebScraper:
    """Web scraper for Instagram public profiles."""

    def __init__(self, username: str, output_path: Path):
        self.username = username
        self.output_path = output_path
        self.session = requests.Session()
        self.wods: Dict[str, str] = {}
        self._setup_session()

    def _setup_session(self):
        """Setup requests session with appropriate headers."""
        self.session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        })

    def _clean_wod_text(self, text: str) -> str:
        """Clean WOD text by removing promotional hashtags and trimming whitespace."""
        cleaned = text
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

    def _fetch_profile_page(self) -> Optional[str]:
        """Fetch the Instagram profile page HTML."""
        url = f"https://www.instagram.com/{self.username}/"

        try:
            logger.info(f"Fetching profile page: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch profile page: {e}")
            return None

    def _extract_shared_data(self, html: str) -> Optional[dict]:
        """Extract shared data JSON from Instagram HTML."""
        # Try to find window._sharedData
        patterns = [
            r'window\._sharedData\s*=\s*({.+?});</script>',
            r'window\.__additionalDataLoaded\([^,]+,\s*({.+?})\);',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    logger.info("Successfully extracted shared data")
                    return data
                except json.JSONDecodeError:
                    continue

        return None

    def _extract_posts_from_shared_data(self, data: dict) -> List[dict]:
        """Extract posts from shared data structure."""
        posts = []

        try:
            # Navigate the data structure to find posts
            # Structure: entry_data.ProfilePage[0].graphql.user.edge_owner_to_timeline_media.edges
            profile_page = data.get('entry_data', {}).get('ProfilePage', [{}])[0]
            user_data = profile_page.get('graphql', {}).get('user', {})
            timeline = user_data.get('edge_owner_to_timeline_media', {})
            edges = timeline.get('edges', [])

            for edge in edges:
                node = edge.get('node', {})
                posts.append({
                    'id': node.get('id'),
                    'timestamp': node.get('taken_at_timestamp'),
                    'caption': self._get_caption(node),
                })

            logger.info(f"Extracted {len(posts)} posts from shared data")
        except Exception as e:
            logger.error(f"Error extracting posts: {e}")

        return posts

    def _get_caption(self, node: dict) -> str:
        """Extract caption from post node."""
        try:
            edges = node.get('edge_media_to_caption', {}).get('edges', [])
            if edges:
                return edges[0].get('node', {}).get('text', '')
        except Exception:
            pass
        return ''

    def _try_graphql_endpoint(self) -> List[dict]:
        """Try to fetch posts using Instagram's GraphQL endpoint."""
        posts = []

        # First, get the profile page to extract necessary data
        html = self._fetch_profile_page()
        if not html:
            return posts

        # Try to extract user ID from the page
        user_id_match = re.search(r'"profilePage_([0-9]+)"', html)
        if not user_id_match:
            user_id_match = re.search(r'"id":"([0-9]+)"', html)

        if not user_id_match:
            logger.warning("Could not find user ID in profile page")
            return posts

        user_id = user_id_match.group(1)
        logger.info(f"Found user ID: {user_id}")

        # Try GraphQL endpoint
        query_hash = "69cba40317214236af40e7efa697781d"  # Public posts query hash
        variables = json.dumps({
            "id": user_id,
            "first": 12,
        })

        graphql_url = f"https://www.instagram.com/graphql/query/?query_hash={query_hash}&variables={variables}"

        try:
            time.sleep(random.uniform(1, 3))
            response = self.session.get(graphql_url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                edges = data.get('data', {}).get('user', {}).get('edge_owner_to_timeline_media', {}).get('edges', [])

                for edge in edges:
                    node = edge.get('node', {})
                    posts.append({
                        'id': node.get('id'),
                        'timestamp': node.get('taken_at_timestamp'),
                        'caption': self._get_caption(node),
                    })

                logger.info(f"Extracted {len(posts)} posts from GraphQL")
            else:
                logger.warning(f"GraphQL endpoint returned {response.status_code}")
        except Exception as e:
            logger.warning(f"GraphQL endpoint failed: {e}")

        return posts

    def _try_embed_endpoint(self, shortcode: str) -> Optional[dict]:
        """Try to get post data from embed endpoint."""
        url = f"https://www.instagram.com/p/{shortcode}/embed/"

        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                # Parse embed page for caption
                soup = BeautifulSoup(response.text, 'html.parser')
                caption_elem = soup.select_one('.Caption')
                if caption_elem:
                    return {'caption': caption_elem.get_text()}
        except Exception as e:
            logger.debug(f"Embed endpoint failed for {shortcode}: {e}")

        return None

    def run(self, stop_on_existing: bool = False) -> Dict[str, str]:
        """Run the web scraper."""
        logger.info(f"Starting web scraper for @{self.username}")

        # Load existing WODs
        self.wods = self._load_existing_wods()
        existing_dates = set(self.wods.keys())
        logger.info(f"Loaded {len(existing_dates)} existing WODs")

        # Try different methods to get posts
        posts = []

        # Method 1: Try extracting from profile page shared data
        html = self._fetch_profile_page()
        if html:
            shared_data = self._extract_shared_data(html)
            if shared_data:
                posts = self._extract_posts_from_shared_data(shared_data)

        # Method 2: Try GraphQL endpoint
        if not posts:
            logger.info("Trying GraphQL endpoint...")
            posts = self._try_graphql_endpoint()

        if not posts:
            logger.warning("Could not extract any posts. Instagram may have blocked the request.")
            logger.info("Consider running locally or trying again later.")
            return self.wods

        # Process posts
        new_count = 0
        for post in posts:
            timestamp = post.get('timestamp')
            caption = post.get('caption', '')

            if not timestamp or not caption:
                continue

            # Convert timestamp to date
            post_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

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

        # Save results
        if new_count > 0:
            self._save_wods()
            logger.info(f"Saved {new_count} new WODs (total: {len(self.wods)})")
        else:
            logger.info("No new WODs found")

        return self.wods


def main():
    parser = argparse.ArgumentParser(
        description="Instagram Web Scraper for WOD Tracker"
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
    print("Instagram Web Scraper for WOD Tracker")
    print("=" * 60)
    print(f"Target account: @{args.username}")
    print(f"Output file: {output_path}")
    print(f"Stop on existing: {args.stop_on_existing}")
    print("=" * 60)

    scraper = InstagramWebScraper(args.username, output_path)
    scraper.run(stop_on_existing=args.stop_on_existing)


if __name__ == "__main__":
    main()
