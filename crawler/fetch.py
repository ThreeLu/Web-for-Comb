#!/usr/bin/env python3
"""
arXiv paper fetcher for Comb-Search.

Scrapes arXiv listing pages (/list/{cat}/new) for new papers.
Fetches abstracts individually from /abs/{id} pages.
"""

import argparse
import json
import re
import ssl
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# macOS SSL
ssl._create_default_https_context = ssl._create_unverified_context

CATEGORIES = ["math.CO", "math.NT", "math.PR", "math.GR"]

# Papers must have at least one of these in their category list to be kept.
# This filters out pure probability / statistics / CS papers that aren't
# cross-listed to combinatorics, number theory, or group theory.
REQUIRED_CATEGORIES = {"math.CO", "math.NT", "math.GR"}
BASE_URL = "https://arxiv.org"
HEADERS = {"User-Agent": "Comb-Search/0.2"}


def parse_args():
    p = argparse.ArgumentParser(description="Fetch arXiv papers")
    p.add_argument("--date", type=str, help="Date YYYY-MM-DD")
    p.add_argument("--output-dir", type=str, default="data")
    p.add_argument("--categories", type=str, nargs="+", default=CATEGORIES)
    return p.parse_args()


def fetch_url(url: str) -> str:
    """Fetch a URL and return decoded HTML."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_listing(html: str) -> list[dict]:
    """
    Parse arXiv listing page HTML.
    Only extracts papers from the "New submissions" section
    (skips cross-lists and replacements).
    Returns list of {id, title, authors, categories}.
    """
    # Extract only the "New submissions" section
    # Structure: <h3>New submissions</h3> ... <dt>/<dd> pairs ... <h3>Cross submissions</h3>
    new_section_match = re.search(
        r'<h3[^>]*>New submissions.*?</h3>(.*?)(?:<h3[^>]*>|$)',
        html, re.DOTALL
    )
    if not new_section_match:
        return []

    section_html = new_section_match.group(1)

    dt_blocks = re.findall(r'<dt>(.*?)</dt>', section_html, re.DOTALL)
    dd_blocks = re.findall(r'<dd>(.*?)</dd>', section_html, re.DOTALL)

    papers = []
    for i, dt_html in enumerate(dt_blocks):
        id_match = re.search(r'href\s*=\s*["\']/abs/(\d+\.\d+)["\']', dt_html)
        if not id_match:
            continue
        arxiv_id = id_match.group(1)

        paper = {"id": arxiv_id, "title": "", "authors": "", "categories": []}

        if i < len(dd_blocks):
            dd_html = dd_blocks[i]

            title_match = re.search(
                r'<div\s+class=[\"\']list-title[^\"\']*[\"\']>(.*?)</div>', dd_html, re.DOTALL
            )
            if title_match:
                title = title_match.group(1).strip()
                title = re.sub(r'<[^>]+>', '', title)
                title = re.sub(r'^Title:\s*', '', title)
                title = re.sub(r'\s+', ' ', title).strip()
                paper["title"] = unescape_html(title)

            auth_match = re.search(
                r'<div\s+class=[\"\']list-authors[\"\']>(.*?)</div>', dd_html, re.DOTALL
            )
            if auth_match:
                auth_html = auth_match.group(1).strip()
                author_names = re.findall(r'<a[^>]*>([^<]+)</a>', auth_html)
                if author_names:
                    paper["authors"] = ", ".join(author_names)

            subj_match = re.search(
                r'<div\s+class=[\"\']list-subjects[\"\']>(.*?)</div>', dd_html, re.DOTALL
            )
            if subj_match:
                subj_text = subj_match.group(1).strip()
                subj_text = re.sub(r'<[^>]+>', '', subj_text)
                cats = re.findall(r'\(([a-z-]+\.[A-Z]{2})\)', subj_text)
                paper["categories"] = list(dict.fromkeys(cats))

        papers.append(paper)

    return papers


def unescape_html(text: str) -> str:
    """Unescape common HTML entities in arXiv abstracts."""
    return (text
        .replace('&gt;', '>')
        .replace('&lt;', '<')
        .replace('&amp;', '&')
        .replace('&quot;', '"')
        .replace('&#39;', "'")
        .replace('&apos;', "'")
    )


def fetch_abstract(arxiv_id: str) -> str:
    """Fetch paper abstract from /abs/{id} page."""
    try:
        html = fetch_url(f"{BASE_URL}/abs/{arxiv_id}")
    except Exception:
        return ""

    m = re.search(
        r'<blockquote class="abstract[^"]*">\s*<span class="descriptor">Abstract:</span>\s*(.*?)</blockquote>',
        html,
        re.DOTALL,
    )
    if not m:
        return ""

    abstract = m.group(1).strip()
    abstract = re.sub(r'<[^>]+>', '', abstract)
    abstract = re.sub(r'\s+', ' ', abstract)
    return unescape_html(abstract.strip())


def run(categories: list[str], target_date: str, output_dir: str) -> int:
    """Main fetch logic. Returns number of papers fetched."""
    all_papers = []
    seen_ids = set()

    for cat in categories:
        print(f"Fetching {cat}...", file=sys.stderr)
        try:
            html = fetch_url(f"{BASE_URL}/list/{cat}/new")
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            continue

        papers = parse_listing(html)
        print(f"  → {len(papers)} papers listed", file=sys.stderr)

        count = 0
        for i, p in enumerate(papers):
            pid = p["id"]
            if pid in seen_ids:
                continue
            seen_ids.add(pid)

            # Rate-limit: pause every 10 requests
            if i > 0 and i % 10 == 0:
                time.sleep(1)

            abstract = fetch_abstract(pid)
            authors_list = [a.strip() for a in p.get("authors", "").split(",") if a.strip()]

            all_papers.append({
                "id": pid,
                "title": p.get("title", ""),
                "authors": authors_list,
                "summary": abstract,
                "categories": p.get("categories", [cat]),
                "published": target_date,
                "abs": f"{BASE_URL}/abs/{pid}",
                "pdf": f"{BASE_URL}/pdf/{pid}",
                "comment": "",
                "journal_ref": "",
                "doi": "",
            })
            count += 1

            print(f"  → {count} papers with abstracts", file=sys.stderr)

    # Filter: keep only papers with at least one required category
    before = len(all_papers)
    all_papers = [
        p for p in all_papers
        if REQUIRED_CATEGORIES & set(p["categories"])
    ]
    if before != len(all_papers):
        print(f"  Category filter: {before} → {len(all_papers)} papers kept", file=sys.stderr)

    # Save
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{target_date}.jsonl"

    with open(out_file, "w", encoding="utf-8") as f:
        for paper in all_papers:
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")

    print(f"\nTotal: {len(all_papers)} → {out_file}", file=sys.stderr)
    return len(all_papers)


if __name__ == "__main__":
    args = parse_args()
    target_date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Date: {target_date}", file=sys.stderr)
    total = run(args.categories, target_date, args.output_dir)
    print(total)
