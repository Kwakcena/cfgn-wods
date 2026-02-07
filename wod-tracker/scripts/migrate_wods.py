#!/usr/bin/env python3
"""One-time migration script to strip W.O.D date prefixes from wods.json content
and re-key entries based on the date extracted from content."""

import json
import logging
import sys
from pathlib import Path
from typing import Dict

from wod_utils import extract_wod_date, strip_wod_date_prefix

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def migrate_wods_data(data: Dict[str, str]) -> Dict[str, str]:
    """Migrate WOD data: re-key by content date and strip prefixes.

    Args:
        data: Original {date_key: content} dictionary.

    Returns:
        New dictionary with content-derived keys and stripped content,
        sorted in descending order.
    """
    migrated: Dict[str, str] = {}

    for original_key, content in data.items():
        content_date = extract_wod_date(content)
        new_key = content_date if content_date else original_key
        stripped_content = strip_wod_date_prefix(content)

        # Handle key conflicts
        if new_key in migrated:
            idx = 2
            while f"{new_key}-{idx}" in migrated:
                idx += 1
            conflict_key = f"{new_key}-{idx}"
            logger.warning(
                f"Key conflict: {original_key} -> {new_key} (using {conflict_key})"
            )
            new_key = conflict_key

        if new_key != original_key:
            logger.info(f"Re-keyed: {original_key} -> {new_key}")

        migrated[new_key] = stripped_content

    return dict(sorted(migrated.items(), reverse=True))


def main() -> None:
    """Run migration on the actual wods.json file."""
    script_dir = Path(__file__).parent
    wods_path = script_dir.parent / "src" / "data" / "wods.json"

    if not wods_path.exists():
        logger.error(f"wods.json not found at {wods_path}")
        sys.exit(1)

    with open(wods_path, "r", encoding="utf-8") as f:
        original_data = json.load(f)

    logger.info(f"Loaded {len(original_data)} entries from {wods_path}")

    # Create backup
    backup_path = wods_path.with_suffix(".json.bak")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(original_data, f, indent=2, ensure_ascii=False)
    logger.info(f"Backup saved to {backup_path}")

    migrated_data = migrate_wods_data(original_data)

    assert len(migrated_data) == len(original_data), (
        f"Entry count mismatch: {len(migrated_data)} vs {len(original_data)}"
    )

    with open(wods_path, "w", encoding="utf-8") as f:
        json.dump(migrated_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Migration complete. Saved {len(migrated_data)} entries to {wods_path}")


if __name__ == "__main__":
    main()
