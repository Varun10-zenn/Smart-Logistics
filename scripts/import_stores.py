"""
CLI script to import Zepto store locations as warehouses.
Usage:
    python scripts/import_stores.py data/zepto_stores_chennai_vellore.csv --yes
"""
import sys
import os
import argparse
from pathlib import Path

# Ensure root directory is in sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.services.warehouse_service import import_stores_csv


def main():
    parser = argparse.ArgumentParser(description="Import Zepto store locations into database.")
    parser.add_argument("csv_path", type=str, help="Path to stores CSV file")
    parser.add_argument("--yes", action="store_true", help="Bypass confirmation prompt")
    parser.add_argument("--no-layout", action="store_true", help="Disable layout generation")
    parser.add_argument("--aisles", type=int, default=4, help="Aisles per store")
    parser.add_argument("--shelves", type=int, default=5, help="Shelves per aisle")

    args = parser.parse_args()

    if not os.path.exists(args.csv_path):
        print(f"Error: File '{args.csv_path}' not found.")
        sys.exit(1)

    if not args.yes:
        confirm = input(f"Import stores from '{args.csv_path}' into DB? (y/N): ")
        if confirm.lower() not in ("y", "yes"):
            print("Import aborted.")
            sys.exit(0)

    print(f"Reading CSV file '{args.csv_path}'...")
    with open(args.csv_path, "r", encoding="utf-8") as f:
        content = f.read()

    db = SessionLocal()
    try:
        res = import_stores_csv(
            db=db,
            csv_content=content,
            generate_layout=not args.no_layout,
            aisles=args.aisles,
            shelves_per_aisle=args.shelves,
        )
        print("\n--- STORE IMPORT COMPLETED ---")
        print(f"Created: {res['created']}")
        print(f"Updated: {res['updated']}")
        print(f"Skipped: {res['skipped']}")
        if res['errors']:
            print(f"\nErrors ({len(res['errors'])}):")
            for err in res['errors']:
                print(f"  Row {err['row']}: {err['message']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
