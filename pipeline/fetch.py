#!/usr/bin/env python3
"""
arXiv paper fetcher for Comb-Search.

Two-stage design:
  1. Scrape arXiv's /list/{cat}/new pages to get the exact set of *new
     submissions* announced today (the arXiv API has no clean equivalent).
  2. Batch-fetch metadata (abstract, real submission date, authors, categories,
     doi, comment) for those IDs via the arXiv API `id_list` endpoint — one
     request per 100 papers instead of one HTTP request per abstract.

If the API misses an ID, we fall back to what the listing page gave us, so a
paper is never dropped just because metadata enrichment failed.

Categories and the required-category filter are configurable via env vars:
  ARXIV_CATEGORIES           default: math.CO math.NT math.PR math.GR
  ARXIV_REQUIRED_CATEGORIES  keep only papers carrying one of these
                             (default: math.CO math.NT math.GR)
"""

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

# macOS ships an OpenSSL that fails to verify arXiv's chain in some setups.
ssl._create_default_https_context = ssl._create_unverified_context

ATOM = "http://www.w3.org/2005/Atom"
ARXIV = "http://arxiv.org/schemas/atom"
NS = {"a": ATOM, "arxiv": ARXIV}


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        return default
    return [c.strip() for c in re.split(r"[,\s]+", raw) if c.strip()]


CATEGORIES = _env_list("ARXIV_CATEGORIES", ["math.CO", "math.NT", "math.PR", "math.GR"])
REQUIRED_CATEGORIES = set(
    _env_list("ARXIV_REQUIRED_CATEGORIES", ["math.CO", "math.NT", "math.GR"])
)
BASE_URL = "https://arxiv.org"
API_URL = "https://export.arxiv.org/api/query"
API_BATCH = 100
API_PAUSE = 3.0  # arXiv API etiquette: >=3s between requests
HEADERS = {"User-Agent": "Comb-Search/0.4 (+https://github.com/ThreeLu/Web-for-Comb)"}


def parse_args():
    p = argparse.ArgumentParser(description="Fetch arXiv papers")
    p.add_argument("--date", type=str, help="Date YYYY-MM-DD")
    p.add_argument("--output-dir", type=str, default="data")
    p.add_argument("--categories", type=str, nargs="+", default=CATEGORIES)
    return p.parse_args()


def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def unescape_html(text: str) -> str:
    return (text
        .replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')
        .replace('&quot;', '"').replace('&#39;', "'").replace('&apos;', "'"))


def parse_listing(html: str) -> list[dict]:
    """
    Parse an arXiv listing page. Only the "New submissions" section (skips
    cross-lists and replacements). Returns [{id, title, authors, categories}].
    """
    new_section_match = re.search(
        r'<h3[^>]*>New submissions.*?</h3>(.*?)(?:<h3[^>]*>|$)', html, re.DOTALL
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
        paper = {"id": id_match.group(1), "title": "", "authors": "", "categories": []}
        if i < len(dd_blocks):
            dd_html = dd_blocks[i]
            title_match = re.search(
                r'<div\s+class=[\"\']list-title[^\"\']*[\"\']>(.*?)</div>', dd_html, re.DOTALL)
            if title_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1).strip())
                title = re.sub(r'^Title:\s*', '', title)
                paper["title"] = unescape_html(re.sub(r'\s+', ' ', title).strip())
            auth_match = re.search(
                r'<div\s+class=[\"\']list-authors[\"\']>(.*?)</div>', dd_html, re.DOTALL)
            if auth_match:
                names = re.findall(r'<a[^>]*>([^<]+)</a>', auth_match.group(1))
                if names:
                    paper["authors"] = ", ".join(names)
            subj_match = re.search(
                r'<div\s+class=[\"\']list-subjects[\"\']>(.*?)</div>', dd_html, re.DOTALL)
            if subj_match:
                subj_text = re.sub(r'<[^>]+>', '', subj_match.group(1).strip())
                paper["categories"] = list(dict.fromkeys(
                    re.findall(r'\(([a-z-]+\.[A-Z]{2})\)', subj_text)))
        papers.append(paper)
    return papers


def parse_api_feed(xml_text: str) -> dict[str, dict]:
    """Parse an arXiv API Atom feed into {bare_id: metadata}."""
    out: dict[str, dict] = {}
    root = ET.fromstring(xml_text)
    for e in root.findall("a:entry", NS):
        idurl = e.findtext("a:id", "", NS)
        bare = re.sub(r"v\d+$", "", idurl.rsplit("/abs/", 1)[-1].strip())
        if not bare:
            continue
        primary = e.find("arxiv:primary_category", NS)
        cats = [primary.get("term")] if primary is not None else []
        for c in e.findall("a:category", NS):
            term = c.get("term")
            if term and term not in cats:
                cats.append(term)
        title = re.sub(r"\s+", " ", (e.findtext("a:title", "", NS) or "").strip())
        authors = [a.findtext("a:name", "", NS).strip()
                   for a in e.findall("a:author", NS)
                   if a.findtext("a:name", "", NS)]
        out[bare] = {
            "title": title,
            "authors": authors,
            "summary": re.sub(r"\s+", " ", (e.findtext("a:summary", "", NS) or "").strip()),
            "categories": cats,
            "published": (e.findtext("a:published", "", NS) or "")[:10],
            "doi": e.findtext("arxiv:doi", "", NS) or "",
            "comment": (e.findtext("arxiv:comment", "", NS) or "").strip(),
            "journal_ref": e.findtext("arxiv:journal_ref", "", NS) or "",
        }
    return out


def fetch_metadata(ids: list[str]) -> dict[str, dict]:
    """Batch-fetch metadata for IDs via the arXiv API (chunks of 100)."""
    meta: dict[str, dict] = {}
    for i in range(0, len(ids), API_BATCH):
        chunk = ids[i : i + API_BATCH]
        url = f"{API_URL}?id_list={','.join(chunk)}&max_results={len(chunk)}"
        try:
            xml_text = fetch_url(url)
            meta.update(parse_api_feed(xml_text))
        except Exception as e:  # noqa: BLE001
            print(f"  API batch failed ({len(chunk)} ids): {e}", file=sys.stderr)
        if i + API_BATCH < len(ids):
            time.sleep(API_PAUSE)
    return meta


def run(categories: list[str], target_date: str, output_dir: str) -> int:
    # Stage 1: scrape listings for the new-submission ID set (ordered, unique).
    listing: list[dict] = []
    seen = set()
    for cat in categories:
        print(f"Fetching {cat} listing...", file=sys.stderr)
        try:
            html = fetch_url(f"{BASE_URL}/list/{cat}/new")
        except Exception as e:  # noqa: BLE001
            print(f"  Error: {e}", file=sys.stderr)
            continue
        found = parse_listing(html)
        print(f"  -> {len(found)} new submissions", file=sys.stderr)
        for p in found:
            if p["id"] not in seen:
                seen.add(p["id"])
                listing.append(p)

    if not listing:
        _write([], output_dir, target_date)
        return 0

    # Stage 2: enrich with API metadata (batched).
    ids = [p["id"] for p in listing]
    print(f"Fetching metadata for {len(ids)} papers via arXiv API...", file=sys.stderr)
    meta = fetch_metadata(ids)
    print(f"  -> metadata for {len(meta)}/{len(ids)} papers", file=sys.stderr)

    all_papers = []
    for p in listing:
        pid = p["id"]
        m = meta.get(pid, {})
        categories_final = m.get("categories") or p.get("categories") or []
        all_papers.append({
            "id": pid,
            "title": m.get("title") or p.get("title", ""),
            "authors": m.get("authors") or [
                a.strip() for a in p.get("authors", "").split(",") if a.strip()],
            "summary": m.get("summary", ""),
            "categories": categories_final,
            "published": m.get("published") or target_date,
            "abs": f"{BASE_URL}/abs/{pid}",
            "pdf": f"{BASE_URL}/pdf/{pid}",
            "comment": m.get("comment", ""),
            "journal_ref": m.get("journal_ref", ""),
            "doi": m.get("doi", ""),
        })

    before = len(all_papers)
    all_papers = [p for p in all_papers if REQUIRED_CATEGORIES & set(p["categories"])]
    if before != len(all_papers):
        print(f"  Category filter: {before} -> {len(all_papers)} papers kept", file=sys.stderr)

    _write(all_papers, output_dir, target_date)
    return len(all_papers)


def _write(papers: list[dict], output_dir: str, target_date: str):
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{target_date}.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for paper in papers:
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")
    print(f"\nTotal: {len(papers)} -> {out_file}", file=sys.stderr)


if __name__ == "__main__":
    args = parse_args()
    target_date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Date: {target_date}", file=sys.stderr)
    total = run(args.categories, target_date, args.output_dir)
    print(total)
