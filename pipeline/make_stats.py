#!/usr/bin/env python3
"""
Build assets/stats.json — aggregate stats over all history, for the trend bar
and (later) a statistics view.

  {
    "generated": "2026-07-07T...",
    "total_days": 12,
    "total_matched": 96,
    "daily":    [{"date": "2026-06-20", "matched": 8, "fetched": 35}, ...],
    "keywords": [["Hamilton cycle", 12], ...],   # most common first
    "authors":  [["Benny Sudakov", 4], ...]
  }
"""

import argparse
import datetime
import json
import sys
from collections import Counter
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    papers = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    papers.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return papers


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path) as f:
        return sum(1 for line in f if line.strip())


def main():
    parser = argparse.ArgumentParser(description="Build stats.json")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--output", default="assets/stats.json")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    files = sorted(data_dir.glob("*_ai_enhanced.jsonl"))

    daily = []
    kw_freq: Counter = Counter()
    au_freq: Counter = Counter()
    total_matched = 0

    for path in files:
        date = path.name[: len("YYYY-MM-DD")]
        papers = load_jsonl(path)
        matched = len(papers)
        total_matched += matched
        daily.append({
            "date": date,
            "matched": matched,
            "fetched": count_lines(data_dir / f"{date}.jsonl"),
        })
        for p in papers:
            reasons = p.get("match_reasons") or {}
            kw_freq.update(reasons.get("keywords", []))
            au_freq.update(reasons.get("authors", []))

    stats = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "total_days": len(daily),
        "total_matched": total_matched,
        "daily": daily,
        "keywords": kw_freq.most_common(50),
        "authors": au_freq.most_common(50),
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"Wrote stats for {len(daily)} days ({total_matched} matched) to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
