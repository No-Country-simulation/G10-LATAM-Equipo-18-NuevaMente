#!/usr/bin/env python3
"""
purge_orphan_vector_stores.py

Purpose:
    Removes the FAISS index directories that no longer belong to a document.
    A directory is an orphan when the `documents` table has no row with that
    document_id, which happens when a document was deleted from the database
    without removing its index, or when an ingestion run was interrupted.

    The script never deletes anything unless --confirm is passed: the default
    run only prints what would be removed.

Input:
    - --confirm: actually remove the directories. Without it the script only
      reports what it would do.
    - --store-dir PATH: vector store directory to inspect. Defaults to the
      configured VECTOR_STORE_DIR.

Output:
    A report of the orphaned index directories, and a non-zero exit code when
    a directory could not be removed.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.services.document_repository import get_document_repository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remove vector store directories without a document row.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Remove the directories. Without this flag nothing is deleted.",
    )
    parser.add_argument(
        "--store-dir",
        default=settings.VECTOR_STORE_DIR,
        help="Vector store directory to inspect.",
    )
    return parser.parse_args()


def find_orphans(store_dir: Path) -> list:
    """Returns the names of the index directories without a document row."""
    if not store_dir.exists():
        return []

    known_ids = {record.document_id for record in get_document_repository().list_documents()}
    return sorted(
        entry.name
        for entry in store_dir.iterdir()
        if entry.is_dir() and entry.name not in known_ids
    )


def main() -> int:
    args = parse_args()
    store_dir = Path(args.store_dir)

    orphans = find_orphans(store_dir)
    if not orphans:
        print("[*] No orphaned vector store directories found.")
        return 0

    mode = "EXECUTE" if args.confirm else "DRY-RUN"
    print("=" * 70)
    print(f"  NUEVAMENTE - ORPHAN VECTOR STORE GC [{mode}]")
    print(f"  Store directory: {store_dir.resolve()}")
    print("=" * 70)
    for name in orphans:
        print(f"  - {name}")

    if not args.confirm:
        print("-" * 70)
        print(f"[i] {len(orphans)} orphan directory(ies) would be removed. Re-run with --confirm to remove them.")
        return 0

    failures = 0
    for name in orphans:
        try:
            shutil.rmtree(store_dir / name)
            print(f"[OK] {name} removed.")
        except OSError as exc:
            failures += 1
            print(f"[ERROR] {name}: {exc}")

    print("-" * 70)
    print(f"[i] {len(orphans) - failures} removed, {failures} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
