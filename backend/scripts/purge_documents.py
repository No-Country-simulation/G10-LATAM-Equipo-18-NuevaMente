#!/usr/bin/env python3
"""
purge_documents.py

Purpose:
    Permanently deletes indexed documents through the same service the HTTP
    endpoint uses, so object storage, the vector index and the metadata row
    are always removed in the same order.

    The script never deletes anything unless --confirm is passed: the default
    run only prints what would be deleted.

Input:
    - --document-id ID: delete only this document (repeatable).
    - --all: delete every document of the repository.
    - --confirm: actually perform the deletion. Without it the script only
      reports what it would do.
    - --include-processing: also delete the documents that are still being
      processed. They are skipped by default because the ingestion thread
      would recreate their index.

Output:
    A report of the planned or performed deletions, and a non-zero exit code
    when a deletion failed.
"""

import argparse
import os
import sys
from typing import List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException

from app.services.document_deletion_service import get_document_deletion_service
from app.services.document_repository import get_document_repository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Purge indexed documents from every storage layer.")
    parser.add_argument(
        "--document-id",
        action="append",
        default=[],
        dest="document_ids",
        help="Document id to delete. Repeat the flag to delete several.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Target every document of the repository.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Perform the deletion. Without this flag nothing is deleted.",
    )
    parser.add_argument(
        "--include-processing",
        action="store_true",
        help="Also delete the documents whose status is 'processing'.",
    )
    return parser.parse_args()


def select_targets(document_ids: List[str], delete_all: bool, include_processing: bool):
    """Returns the (document_id, title, object_key, status) rows to delete."""
    repo = get_document_repository()

    if document_ids:
        rows = []
        for document_id in document_ids:
            record = repo.get_document(document_id)
            if record is None:
                print(f"[!] Document '{document_id}' does not exist.")
                continue
            rows.append(record)
        return rows

    if not delete_all:
        print("[!] No target selected. Use --document-id ID or --all.")
        return []

    records = repo.list_documents()
    if include_processing:
        return records
    return [record for record in records if record.status != "processing"]


def main() -> int:
    args = parse_args()
    records = select_targets(args.document_ids, args.all, args.include_processing)

    if not records:
        print("[*] Nothing to delete.")
        return 0

    mode = "EXECUTE" if args.confirm else "DRY-RUN"
    print("=" * 70)
    print(f"  NUEVAMENTE - DOCUMENT PURGE [{mode}]")
    print("=" * 70)
    for record in records:
        print(f"  - {record.document_id} | {record.status:10s} | {record.title} | {record.object_key}")

    if not args.confirm:
        print("-" * 70)
        print(f"[i] {len(records)} document(s) would be deleted. Re-run with --confirm to delete them.")
        return 0

    service = get_document_deletion_service()
    failures = 0
    for record in records:
        try:
            service.delete_document(document_id=record.document_id, requester_id=None)
            print(f"[OK] {record.document_id} deleted.")
        except HTTPException as exc:
            failures += 1
            print(f"[ERROR] {record.document_id}: {exc.status_code} {exc.detail}")

    print("-" * 70)
    print(f"[i] {len(records) - failures} deleted, {failures} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
