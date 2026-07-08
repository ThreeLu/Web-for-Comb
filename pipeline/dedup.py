#!/usr/bin/env python3
"""
Deduplicate today's papers against recent history.
Removes papers already seen in the last N days.

Operates in place on data/{date}.jsonl (the full fetched set). This file is
kept intact by the rest of the pipeline so it remains a complete record for
future dedup runs.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def load_ids(filepath: Path) -> set[str]:
    """Load all paper IDs from a JSONL file."""
    if not filepath.exists():
        return set()
    ids = set()
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                paper = json.loads(line)
                ids.add(paper.get("id", ""))
            except json.JSONDecodeError:
                continue
    return ids


def main():
    parser = argparse.ArgumentParser(description="Dedup today's papers")
    parser.add_argument("--date", required=True, help="Target date YYYY-MM-DD")
    parser.add_argument(
        "--history-days", type=int, default=7,
        help="Number of past days to check for duplicates (default: 7)"
    )
    parser.add_argument("--data-dir", default="data", help="Data directory")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    today_file = data_dir / f"{args.date}.jsonl"

    if not today_file.exists():
        print(f"No data file for {args.date}", file=sys.stderr)
        sys.exit(0)

    with open(today_file) as f:
        today_papers = [json.loads(line) for line in f if line.strip()]
    print(f"Today's papers (before dedup): {len(today_papers)}", file=sys.stderr)

    history_ids: set[str] = set()
    target_date = datetime.fromisoformat(args.date)
    for i in range(1, args.history_days + 1):
        past_date = (target_date - timedelta(days=i)).strftime("%Y-%m-%d")
        past_file = data_dir / f"{past_date}.jsonl"
        ids = load_ids(past_file)
        history_ids.update(ids)
        if ids:
            print(
                f"  History {past_date}: {len(ids)} IDs (total: {len(history_ids)})",
                file=sys.stderr,
            )

    new_papers = [p for p in today_papers if p.get("id", "") not in history_ids]
    dup_count = len(today_papers) - len(new_papers)
    print(f"Duplicates removed: {dup_count}, New: {len(new_papers)}", file=sys.stderr)

    if new_papers:
        with open(today_file, "w") as f:
            for paper in new_papers:
                f.write(json.dumps(paper, ensure_ascii=False) + "\n")
        print(f"Updated {today_file} with {len(new_papers)} papers", file=sys.stderr)
    else:
        today_file.unlink()
        print(f"All papers are duplicates. Deleted {today_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
