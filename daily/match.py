#!/usr/bin/env python3
"""
Match papers against keyword and author configs.
Adds a `matched` boolean field to each paper in the JSONL.
Runs locally during the daily pipeline — never exposed on the website.
"""

import argparse
import json
import sys
from pathlib import Path

import yaml


def load_config(project_root: Path):
    """Load keywords and authors from YAML configs."""
    keywords = []
    authors = []

    kw_file = project_root / "config" / "keywords.yaml"
    if kw_file.exists():
        with open(kw_file) as f:
            data = yaml.safe_load(f)
            if data and "keywords" in data:
                for group in data["keywords"].values():
                    keywords.extend(group)

    au_file = project_root / "config" / "authors.yaml"
    if au_file.exists():
        with open(au_file) as f:
            data = yaml.safe_load(f)
            if data and "authors" in data:
                authors = data["authors"]

    return keywords, authors


def match_paper(paper: dict, keywords: list[str], authors: list[str]) -> bool:
    """Check if a paper matches any keyword or author."""
    title = (paper.get("title") or "").lower()
    abstract = (paper.get("summary") or "").lower()
    paper_authors = " ".join(paper.get("authors", [])).lower()

    for kw in keywords:
        if kw.lower() in title or kw.lower() in abstract:
            return True
    for au in authors:
        if au.lower() in paper_authors:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Match papers against keyword/author configs"
    )
    parser.add_argument("--data", required=True, help="Path to JSONL file")
    parser.add_argument(
        "--project-root", default=".", help="Project root directory"
    )
    args = parser.parse_args()

    project_root = Path(args.project_root)
    keywords, authors = load_config(project_root)

    if not keywords and not authors:
        print("No keywords or authors configured — skipping match.", file=sys.stderr)
        return

    print(f"Loaded {len(keywords)} keywords, {len(authors)} authors", file=sys.stderr)

    data_file = Path(args.data)
    if not data_file.exists():
        print(f"File not found: {data_file}", file=sys.stderr)
        sys.exit(1)

    papers = []
    with open(data_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            papers.append(json.loads(line))

    matched = []
    for p in papers:
        if match_paper(p, keywords, authors):
            p["matched"] = True
            matched.append(p)

    with open(data_file, "w") as f:
        for p in matched:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(
        f"Kept: {len(matched)}/{len(papers)} matched papers (others discarded)", file=sys.stderr
    )


if __name__ == "__main__":
    main()
