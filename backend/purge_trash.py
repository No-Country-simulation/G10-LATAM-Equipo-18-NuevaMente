#!/usr/bin/env python3
"""
purge_trash.py

CLI script to execute automatic retention purge for trashed contents.
Finds all items where purge_at <= now (or purge_failed = 1), permanently
deletes their OCI Object Storage files under usuarios/{user_id}/... and
removes their database records.

Usage:
    python purge_trash.py [--batch-size 50]
"""

import sys
import argparse
import logging
from app.services.trash_service import TrashService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("purge_trash_cli")


def main():
    parser = argparse.ArgumentParser(description="Purge expired items from NuevaMente trash.")
    parser.add_argument("--batch-size", type=int, default=50, help="Maximum number of items to purge in a single run.")
    args = parser.parse_args()

    logger.info(f"Starting automatic trash retention purge (batch_size={args.batch_size})...")
    trash_service = TrashService()

    try:
        purged_count = trash_service.auto_purge(batch_size=args.batch_size)
        logger.info(f"Purge job finished successfully. Total items purged: {purged_count}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error executing trash purge: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
