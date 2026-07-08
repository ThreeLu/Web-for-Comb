#!/usr/bin/env python3
"""
Build an RSS 2.0 feed (feed.xml) from recent matched papers, so the daily
digest can be consumed in any feed reader instead of visiting the site.

Reads the last N days of data/{date}_ai_enhanced.jsonl and emits one <item> per
matched paper: title, arXiv link, the Chinese TL;DR, and why it matched.
"""

import argparse
import datetime
import json
import sys
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

SITE_URL = "https://threelu.github.io/Web-for-Comb/"
DATE_RE_LEN = len("YYYY-MM-DD")


def load_day(path: Path, date: str) -> list[dict]:
    papers = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                p = json.loads(line)
            except json.JSONDecodeError:
                continue
            p["_date"] = date
            papers.append(p)
    return papers


def cdata(text: str) -> str:
    return "<![CDATA[" + (text or "").replace("]]>", "]]]]><![CDATA[>") + "]]>"


def build_item(p: dict) -> str:
    pid = p.get("id", "")
    title = p.get("title", "(untitled)")
    link = p.get("abs") or f"https://arxiv.org/abs/{pid}"
    ai = p.get("AI") or {}
    tldr = ai.get("tldr", "")
    authors = p.get("authors", [])
    if isinstance(authors, list):
        authors = ", ".join(authors)

    reasons = p.get("match_reasons") or {}
    why_bits = list(reasons.get("keywords", [])) + [f"@{a}" for a in reasons.get("authors", [])]
    why = ("命中: " + ", ".join(why_bits)) if why_bits else ""

    desc_parts = [x for x in (tldr, why, authors) if x]
    description = "<br/><br/>".join(escape(x) for x in desc_parts)

    dt = datetime.datetime.fromisoformat(p["_date"]).replace(tzinfo=datetime.timezone.utc)
    pubdate = format_datetime(dt)

    return (
        "    <item>\n"
        f"      <title>{escape(title)}</title>\n"
        f"      <link>{escape(link)}</link>\n"
        f"      <guid isPermaLink=\"false\">arxiv:{escape(pid)}</guid>\n"
        f"      <pubDate>{pubdate}</pubDate>\n"
        f"      <description>{cdata(description)}</description>\n"
        "    </item>"
    )


def main():
    parser = argparse.ArgumentParser(description="Build RSS feed from matched papers")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--output", default="feed.xml")
    parser.add_argument("--days", type=int, default=14, help="How many recent days to include")
    parser.add_argument("--max-items", type=int, default=200)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    files = sorted(data_dir.glob("*_ai_enhanced.jsonl"), reverse=True)

    papers: list[dict] = []
    for path in files[: args.days]:
        date = path.name[:DATE_RE_LEN]
        papers.extend(load_day(path, date))

    # Newest first; only papers that actually have an AI summary.
    papers = [p for p in papers if p.get("AI")]
    papers.sort(key=lambda p: p["_date"], reverse=True)
    papers = papers[: args.max_items]

    now = format_datetime(datetime.datetime.now(datetime.timezone.utc))
    items = "\n".join(build_item(p) for p in papers)

    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        "    <title>Comb-Search · 组合与图论 arXiv 日报</title>\n"
        f"    <link>{SITE_URL}</link>\n"
        "    <description>每日匹配的组合数学与图论 arXiv 新论文（含中文 TL;DR）。</description>\n"
        "    <language>zh-cn</language>\n"
        f"    <lastBuildDate>{now}</lastBuildDate>\n"
        f'    <atom:link href="{SITE_URL}feed.xml" rel="self" type="application/rss+xml"/>\n'
        f"{items}\n"
        "  </channel>\n"
        "</rss>\n"
    )

    Path(args.output).write_text(feed, encoding="utf-8")
    print(f"Wrote {len(papers)} items to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
