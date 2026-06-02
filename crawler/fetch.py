#!/usr/bin/env python3
"""
arXiv paper fetcher for Comb-Search.

Fetches new papers from arXiv for specified categories using the arXiv API.
Outputs JSONL with full paper metadata: id, title, authors, abstract,
categories, submitted date, and arXiv URLs.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import arxiv


CATEGORIES = ["math.CO", "math.NT", "math.PR", "cs.DM"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch today's arXiv papers for combinatorics categories"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Date in YYYY-MM-DD format (default: today UTC)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data",
        help="Output directory for JSONL files (default: data/)",
    )
    parser.add_argument(
        "--categories",
        type=str,
        nargs="+",
        default=CATEGORIES,
        help=f"arXiv categories to fetch (default: {', '.join(CATEGORIES)})",
    )
    return parser.parse_args()


def paper_to_dict(paper: arxiv.Result) -> dict:
    """Convert an arxiv.Result to our standard JSONL dict."""
    return {
        "id": paper.get_short_id(),
        "title": paper.title,
        "authors": [a.name for a in paper.authors],
        "summary": paper.summary,
        "categories": list(paper.categories),
        "published": paper.published.isoformat(),
        "updated": paper.updated.isoformat(),
        "abs": paper.entry_id,
        "pdf": paper.pdf_url,
        "comment": paper.comment or "",
        "journal_ref": paper.journal_ref or "",
        "doi": paper.doi or "",
    }


def fetch_papers(categories: list[str], target_date: str) -> list[dict]:
    """
    Fetch all new papers for the given categories on target_date.

    Uses arxiv.Search to query the arXiv API, sorted by submitted date,
    filtering to papers that appeared on the target date.
    """
    target = datetime.fromisoformat(target_date).replace(
        tzinfo=timezone.utc
    )
    # We search a window: from target_date 00:00 to target_date 23:59 UTC
    # arXiv API doesn't support exact date filtering, so we get today's
    # new submissions by querying each category's /list/new equivalent.

    all_papers = []
    seen_ids = set()

    for cat in categories:
        print(f"Fetching {cat}...", file=sys.stderr)
        # arXiv listings show papers in reverse chronological order.
        # We query by category and check the submitted date.
        search = arxiv.Search(
            query=f"cat:{cat}",
            sort_by=arxiv.SortCriterion.SubmittedDate,
            max_results=500,  # safety limit per category
        )

        count = 0
        for paper in search.results():
            paper_date = paper.published.date().isoformat()
            if paper_date == target_date:
                pid = paper.get_short_id()
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    all_papers.append(paper_to_dict(paper))
                    count += 1

        print(f"  -> {count} new papers in {cat}", file=sys.stderr)

    return all_papers


def main():
    args = parse_args()
    target_date = args.date or datetime.now(timezone.utc).strftime(
        "%Y-%m-%d"
    )

    print(f"Target date: {target_date}", file=sys.stderr)
    print(
        f"Categories: {', '.join(args.categories)}", file=sys.stderr
    )

    papers = fetch_papers(args.categories, target_date)
    print(
        f"\nTotal unique papers: {len(papers)}", file=sys.stderr
    )

    # Ensure output directory exists
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write JSONL
    out_file = out_dir / f"{target_date}.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for paper in papers:
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")

    print(f"Saved to {out_file}", file=sys.stderr)

    # Print paper count for the shell script to read
    print(len(papers))


if __name__ == "__main__":
    main()
