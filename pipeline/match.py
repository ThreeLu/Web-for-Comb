#!/usr/bin/env python3
"""
Match papers against keyword and author configs.

Reads the full fetched set (data/{date}.jsonl), keeps only papers matching a
tracked keyword or author, tags them with `matched: true` plus a
`match_reasons` object, and writes the subset to a separate output file. The
input file is left untouched so it stays a complete record for deduplication.

Matching uses token boundaries (not raw substrings) so a keyword like
"oriented" no longer fires on "orientation", while an optional trailing "s"
still lets a singular keyword catch its plural ("graph" -> "graphs").

Running this BEFORE AI summarization means we only pay for summaries of papers
we actually keep.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml


def load_config(project_root: Path):
    """Load keywords and authors from YAML configs."""
    keywords: list[str] = []
    authors: list[str] = []

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

    # Drop exact-duplicate keywords while preserving order.
    keywords = list(dict.fromkeys(keywords))
    return keywords, authors


def compile_keyword(kw: str) -> re.Pattern:
    """
    Build a token-boundary regex for a keyword. Boundaries are non-alphanumeric
    (so hyphens/spaces inside the keyword are fine), and an optional trailing
    's' lets a singular keyword also match its simple plural.
    """
    escaped = re.escape(kw.strip())
    return re.compile(rf"(?<![a-z0-9]){escaped}s?(?![a-z0-9])", re.IGNORECASE)


def find_matches(paper: dict, kw_patterns: list[tuple[str, re.Pattern]],
                 authors: list[str]) -> dict:
    """Return {'keywords': [...], 'authors': [...]} of what this paper matched."""
    haystack = f"{paper.get('title') or ''} {paper.get('summary') or ''}"
    paper_authors = " ".join(paper.get("authors", [])).lower()

    kw_hits = [kw for kw, pat in kw_patterns if pat.search(haystack)]
    au_hits = [au for au in authors if au.lower() in paper_authors]
    return {"keywords": kw_hits, "authors": au_hits}


def main():
    parser = argparse.ArgumentParser(
        description="Match papers against keyword/author configs"
    )
    parser.add_argument("--data", required=True, help="Path to input JSONL (full fetched set)")
    parser.add_argument(
        "--output", help="Path for matched-only output (default: <data>.matched.jsonl)"
    )
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report matches and keyword usage without writing any file",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root)
    keywords, authors = load_config(project_root)

    if not keywords and not authors:
        print("No keywords or authors configured — skipping match.", file=sys.stderr)
        return

    kw_patterns = [(kw, compile_keyword(kw)) for kw in keywords]
    print(f"Loaded {len(keywords)} keywords, {len(authors)} authors", file=sys.stderr)

    data_file = Path(args.data)
    if not data_file.exists():
        print(f"File not found: {data_file}", file=sys.stderr)
        sys.exit(1)

    papers = []
    with open(data_file) as f:
        for line in f:
            line = line.strip()
            if line:
                papers.append(json.loads(line))

    matched = []
    usage: Counter = Counter()
    for p in papers:
        reasons = find_matches(p, kw_patterns, authors)
        if reasons["keywords"] or reasons["authors"]:
            p["matched"] = True
            p["match_reasons"] = reasons
            matched.append(p)
            for kw in reasons["keywords"]:
                usage[("keyword", kw)] += 1
            for au in reasons["authors"]:
                usage[("author", au)] += 1

    if args.dry_run:
        print(f"\n=== DRY RUN: {len(matched)}/{len(papers)} would match ===")
        for p in matched:
            r = p["match_reasons"]
            why = ", ".join(r["keywords"] + [f"@{a}" for a in r["authors"]])
            print(f"  • {p.get('title', '')[:70]}  [{why}]")
        print("\n--- Config hits ---")
        for (typ, name), c in usage.most_common():
            print(f"  {typ:8} {c:3}  {name}")
        fired = {name for (_typ, name) in usage}
        never = [kw for kw in keywords if kw not in fired]
        print(f"\nKeywords that never fired today ({len(never)}): {', '.join(never) or '(none)'}")
        return

    out_path = Path(args.output) if args.output else data_file.with_suffix(".matched.jsonl")
    with open(out_path, "w") as f:
        for p in matched:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"Kept: {len(matched)}/{len(papers)} matched papers -> {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
