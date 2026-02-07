"""Shared utility functions for WOD data processing.

Used by both crawl_web.py and crawl_instagram.py to ensure consistent
date extraction, content cleaning, and prefix stripping.
"""

import re
from datetime import datetime
from typing import Optional, Tuple

PROMO_TEXT_TO_REMOVE = [
    "#crossfit #크로스핏 crossfitgangnam  #크로스핏강남 cfgn cfgnej #언주역크로스핏 #크로스핏강남언주 언주역 학동역 역삼역 신논현역 논현로614  025556744",
    "#crossfit #크로스핏 crossfitgangnam\xa0 #크로스핏강남 cfgn cfgnej #언주역크로스핏 #크로스핏강남언주 언주역 학동역 역삼역 신논현역 논현로614\xa0 025556744",
]

# Match "YYYYMMDD" followed by whitespace and W.O.D (case-insensitive)
_WOD_DATE_PATTERN = re.compile(r"(\d{8})\s*W\.?O\.?D", re.IGNORECASE)

# Match the full prefix: "YYYYMMDD W.O.D!!" + trailing whitespace/newlines
_WOD_PREFIX_PATTERN = re.compile(r"^\d{8}\s*W\.?O\.?D!*\s*", re.IGNORECASE)


def extract_wod_date(text: str) -> Optional[str]:
    """Extract the WOD date from content text.

    Looks for pattern 'YYYYMMDD W.O.D' and returns 'YYYY-MM-DD' formatted date.
    Returns None if no valid date pattern is found or if the date is invalid.
    """
    match = _WOD_DATE_PATTERN.search(text)
    if match:
        date_str = match.group(1)
        try:
            dt = datetime.strptime(date_str, "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def strip_wod_date_prefix(text: str) -> str:
    """Strip the 'YYYYMMDD W.O.D!!' prefix from WOD content.

    Removes the date prefix and any trailing whitespace/newlines that follow it.
    If no prefix is found, returns the original text unchanged.
    """
    return _WOD_PREFIX_PATTERN.sub("", text).strip()


def clean_wod_text(text: str) -> str:
    """Clean WOD text by removing promotional hashtags and metadata.

    Unified version of the cleaning logic previously duplicated
    in crawl_web.py and crawl_instagram.py.
    """
    cleaned = text

    # Remove Instagram meta description prefix (from og:description)
    meta_pattern = r'^\d+\s*likes?,?\s*\d*\s*comments?\s*-\s*\w+\s+on\s+[^:]+:\s*"?'
    cleaned = re.sub(meta_pattern, "", cleaned, flags=re.IGNORECASE)

    # Remove trailing quote and period from meta description
    cleaned = re.sub(r'"\.?\s*$', "", cleaned)

    # Remove promotional text
    for promo in PROMO_TEXT_TO_REMOVE:
        cleaned = cleaned.replace(promo, "")

    return cleaned.strip()


def process_wod_entry(text: str) -> Tuple[Optional[str], str]:
    """Process a raw WOD text: extract date key and strip prefix from content.

    Returns (date_key, stripped_content).
    date_key is 'YYYY-MM-DD' or None if no date found.
    """
    date_key = extract_wod_date(text)
    stripped = strip_wod_date_prefix(text)
    return date_key, stripped
