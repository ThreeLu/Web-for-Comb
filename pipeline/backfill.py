#!/usr/bin/env python3
"""
Historical backfill: fetch arXiv submissions in a date range via the API and
write per-day data/{date}.jsonl files (same schema as fetch.py).

Unlike fetch.py (which scrapes today's "new submissions" listing), this queries
the API by submittedDate so we can populate past days. Dates that already have
a *_ai_enhanced.jsonl are skipped by default so existing summaries aren't lost.

Usage:
  python pipeline/backfill.py --start 2026-06-21 --end 2026-07-08
"""
import argparse
import json
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).parent))
import fetch as F  # reuse parse_api_feed, filters

API = "https://export.arxiv.org/api/query"
PAGE = 100
PAUSE = 3.0
TIMEOUT = 90


def urlq(params):
    return API + "?" + urlencode(params)


def get(url, retries=4):
    """Fetch with a generous timeout and retries (API is slow for big pages)."""
    last = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=F.HEADERS)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"    retry {attempt}: {e}", file=sys.stderr)
            time.sleep(PAUSE * attempt)
    raise last


def fetch_category(cat, start, end):
    """Page through all submissions for one category in [start,end]."""
    out = {}
    lo = f"{start.strftime('%Y%m%d')}0000"
    hi = f"{end.strftime('%Y%m%d')}2359"
    start_idx = 0
    while True:
        url = urlq({
            "search_query": f"cat:{cat} AND submittedDate:[{lo} TO {hi}]",
            "start": start_idx, "max_results": PAGE,
            "sortBy": "submittedDate", "sortOrder": "ascending",
        })
        try:
            xml = get(url)
        except Exception as e:  # noqa: BLE001
            print(f"  {cat} page@{start_idx} error: {e}", file=sys.stderr)
            break
        meta = F.parse_api_feed(xml)
        if not meta:
            break
        out.update(meta)
        print(f"  {cat}: +{len(meta)} (total {len(out)})", file=sys.stderr)
        if len(meta) < PAGE:
            break
        start_idx += PAGE
        time.sleep(PAUSE)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--output-dir", default="data")
    ap.add_argument("--overwrite", action="store_true",
                    help="Overwrite dates that already have enhanced data")
    args = ap.parse_args()

    start = datetime.fromisoformat(args.start).date()
    end = datetime.fromisoformat(args.end).date()
    out_dir = Path(args.output_dir)

    all_meta = {}
    for cat in F.CATEGORIES:
        print(f"Fetching {cat} {start}..{end}...", file=sys.stderr)
        all_meta.update(fetch_category(cat, start, end))
        time.sleep(PAUSE)

    # Build records, filter required categories, group by submission date.
    by_date = defaultdict(list)
    for pid, m in all_meta.items():
        cats = m.get("categories") or []
        if not (F.REQUIRED_CATEGORIES & set(cats)):
            continue
        d = m.get("published", "")[:10]
        if not d:
            continue
        by_date[d].append({
            "id": pid,
            "title": m.get("title", ""),
            "authors": m.get("authors", []),
            "summary": m.get("summary", ""),
            "categories": cats,
            "published": d,
            "abs": f"https://arxiv.org/abs/{pid}",
            "pdf": f"https://arxiv.org/pdf/{pid}",
            "comment": m.get("comment", ""),
            "journal_ref": m.get("journal_ref", ""),
            "doi": m.get("doi", ""),
        })

    written = 0
    for d, papers in sorted(by_date.items()):
        if not (start <= date.fromisoformat(d) <= end):
            continue  # API can return a few out-of-range submissions
        enhanced = out_dir / f"{d}_ai_enhanced.jsonl"
        if enhanced.exists() and not args.overwrite:
            print(f"  skip {d}: enhanced exists", file=sys.stderr)
            continue
        papers.sort(key=lambda p: p["id"])
        (out_dir / f"{d}.jsonl").write_text(
            "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in papers))
        written += 1
        print(f"  {d}: {len(papers)} papers", file=sys.stderr)
    print(f"Wrote {written} day files.", file=sys.stderr)


if __name__ == "__main__":
    main()
