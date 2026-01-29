#!/usr/bin/env python3
"""
Instagram crawler for CrossFit WOD Tracker
Fetches posts from an Instagram account and saves them to wods.json
"""

import os
import sys
import json
import argparse
import time
import random
import socket
from pathlib import Path
from datetime import datetime

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


def get_session_file_path(username: str) -> Path:
    """Get the path for storing the session file."""
    return Path.home() / ".config" / "instaloader" / f"session-{username}"


def create_loader(login_user: str = None, login_pass: str = None) -> instaloader.Instaloader:
    """Create and configure an Instaloader instance."""
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        post_metadata_txt_pattern="",
        max_connection_attempts=3,
        request_timeout=30,
    )

    # Try to load existing session
    if login_user:
        session_file = get_session_file_path(login_user)
        if session_file.exists():
            try:
                loader.load_session_from_file(login_user, str(session_file))
                print(f"Loaded existing session for {login_user}")
                return loader
            except Exception as e:
                print(f"Could not load session: {e}")

        # Login with credentials
        if login_pass:
            try:
                loader.login(login_user, login_pass)
                # Save session for future use
                session_file.parent.mkdir(parents=True, exist_ok=True)
                loader.save_session_to_file(str(session_file))
                print(f"Logged in as {login_user} and saved session")
            except instaloader.exceptions.BadCredentialsException:
                print("Error: Invalid Instagram credentials")
                sys.exit(1)
            except instaloader.exceptions.TwoFactorAuthRequiredException:
                print("Error: Two-factor authentication required")
                print("Please login via browser and export session, or disable 2FA temporarily")
                sys.exit(1)
            except Exception as e:
                print(f"Login error: {e}")
                sys.exit(1)

    return loader


def load_existing_wods(output_path: Path) -> dict:
    """Load existing WODs from file if it exists."""
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_wods(wods: dict, output_path: Path):
    """Save WODs to JSON file."""
    # Sort by date (newest first)
    sorted_wods = dict(sorted(wods.items(), reverse=True))

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sorted_wods, f, indent=2, ensure_ascii=False)


def fetch_posts(loader: instaloader.Instaloader, target_username: str, output_path: Path,
                delay_min: float = 1.0, delay_max: float = 3.0, max_posts: int = None) -> dict:
    """Fetch all posts from the target Instagram profile with rate limiting."""

    # Load existing WODs to resume from
    wods = load_existing_wods(output_path)
    existing_dates = set(wods.keys())

    if existing_dates:
        print(f"Loaded {len(existing_dates)} existing WODs, will skip duplicates")

    try:
        print(f"Fetching profile: {target_username}")
        profile = instaloader.Profile.from_username(loader.context, target_username)

        post_count = profile.mediacount
        print(f"Found {post_count} posts")

        if max_posts:
            print(f"Limiting to {max_posts} posts")

        new_count = 0
        skipped_count = 0

        for i, post in enumerate(profile.get_posts(), 1):
            if max_posts and i > max_posts:
                print(f"\nReached max posts limit ({max_posts})")
                break

            # Get post date
            post_date = post.date_local.strftime("%Y-%m-%d")

            # Get caption (may be None)
            caption = post.caption or ""

            # Skip posts without captions
            if not caption.strip():
                print(f"  [{i}/{post_count}] {post_date} - Skipped (no caption)")
                skipped_count += 1
                continue

            # Check if already exists (for resume capability)
            base_date = post_date
            if base_date in existing_dates:
                print(f"  [{i}/{post_count}] {post_date} - Already exists, skipping")
                skipped_count += 1
                continue

            # If multiple posts on same day, append with index
            if post_date in wods:
                idx = 2
                while f"{post_date}-{idx}" in wods:
                    idx += 1
                post_date = f"{post_date}-{idx}"

            wods[post_date] = caption.strip()
            new_count += 1
            print(f"  [{i}/{post_count}] {post_date} - Saved (new: {new_count})")

            # Save periodically (every 10 new posts)
            if new_count % 10 == 0:
                save_wods(wods, output_path)
                print(f"  [Checkpoint] Saved {len(wods)} WODs to file")

            # Random delay to avoid rate limiting
            delay = random.uniform(delay_min, delay_max)
            time.sleep(delay)

    except instaloader.exceptions.ProfileNotExistsException:
        print(f"Error: Profile '{target_username}' does not exist")
        sys.exit(1)
    except instaloader.exceptions.PrivateProfileNotFollowedException:
        print(f"Error: Profile '{target_username}' is private and you're not following it")
        print("Please login with an account that follows this profile")
        sys.exit(1)
    except instaloader.exceptions.LoginRequiredException:
        print("Error: Login required to access this profile")
        print("Please provide credentials via environment variables or arguments")
        sys.exit(1)
    except instaloader.exceptions.QueryReturnedBadRequestException as e:
        print(f"\nRate limited by Instagram. Saving progress...")
        save_wods(wods, output_path)
        print(f"Saved {len(wods)} WODs. Wait a few minutes and run again to resume.")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\nInterrupted! Saving progress...")
        save_wods(wods, output_path)
        print(f"Saved {len(wods)} WODs. Run again to resume.")
        sys.exit(0)
    except Exception as e:
        error_msg = str(e)
        if "wait a few minutes" in error_msg.lower() or "401" in error_msg or "429" in error_msg:
            print(f"\nRate limited by Instagram. Saving progress...")
            save_wods(wods, output_path)
            print(f"Saved {len(wods)} WODs. Wait a few minutes and run again to resume.")
            sys.exit(1)
        print(f"Error fetching posts: {e}")
        # Still save what we have
        if wods:
            save_wods(wods, output_path)
            print(f"Saved {len(wods)} WODs before error.")
        sys.exit(1)

    return wods


def main():
    parser = argparse.ArgumentParser(
        description="Crawl Instagram posts and save to wods.json"
    )
    parser.add_argument(
        "--username",
        "-u",
        default="cfgn_ej",
        help="Instagram username to crawl (default: cfgn_ej)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path (default: src/data/wods.json)"
    )
    parser.add_argument(
        "--login-user",
        default=None,
        help="Your Instagram username for login (or set INSTAGRAM_USER env var)"
    )
    parser.add_argument(
        "--login-pass",
        default=None,
        help="Your Instagram password for login (or set INSTAGRAM_PASS env var)"
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=2.0,
        help="Minimum delay between requests in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=5.0,
        help="Maximum delay between requests in seconds (default: 5.0)"
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=None,
        help="Maximum number of posts to fetch (default: all)"
    )

    args = parser.parse_args()

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        script_dir = Path(__file__).parent
        output_path = script_dir.parent / "src" / "data" / "wods.json"

    # Get login credentials from args or environment
    login_user = args.login_user or os.environ.get("INSTAGRAM_USER")
    login_pass = args.login_pass or os.environ.get("INSTAGRAM_PASS")

    print("=" * 50)
    print("CrossFit WOD Instagram Crawler")
    print("=" * 50)
    print(f"Target account: {args.username}")
    print(f"Output file: {output_path}")
    if login_user:
        print(f"Login as: {login_user}")
    else:
        print("Login: Anonymous (may have limited access)")
    print(f"Delay: {args.delay_min}-{args.delay_max}s between requests")
    if args.max_posts:
        print(f"Max posts: {args.max_posts}")
    print("=" * 50)
    print()

    # Create loader and optionally login
    loader = create_loader(login_user, login_pass)

    # Fetch posts
    wods = fetch_posts(loader, args.username, output_path,
                       args.delay_min, args.delay_max, args.max_posts)

    if not wods:
        print("No posts with captions found!")
        sys.exit(0)

    # Final save
    save_wods(wods, output_path)
    print(f"\nSaved {len(wods)} WODs to {output_path}")
    print("\nDone!")


if __name__ == "__main__":
    main()
