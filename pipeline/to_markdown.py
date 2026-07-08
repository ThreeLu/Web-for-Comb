#!/usr/bin/env python3
"""Render an _ai_enhanced.jsonl file into a browsable Markdown digest."""
import argparse
import json
import os
from itertools import count
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, help="Path to the jsonline file")
    parser.add_argument("--output-prefix", type=str, default=None,
                        help="Output filename prefix (default: derive from input)")
    args = parser.parse_args()

    data = []
    preference = os.environ.get('CATEGORIES', 'math.CO, math.NT, math.PR, cs.DM').split(',')
    preference = list(map(lambda x: x.strip(), preference))

    def rank(cate):
        if cate in preference:
            return preference.index(cate)
        else:
            return len(preference)

    with open(args.data, "r") as f:
        for line in f:
            data.append(json.loads(line))

    categories = set([item["categories"][0] for item in data])
    template_path = Path(__file__).parent / "paper_template.md"
    template = template_path.read_text()
    categories = sorted(categories, key=rank)
    cnt = {cate: 0 for cate in categories}
    for item in data:
        if item["categories"][0] not in cnt.keys():
            continue
        cnt[item["categories"][0]] += 1

    markdown = "<div id=toc></div>\n\n# Table of Contents\n\n"
    for idx, cate in enumerate(categories):
        markdown += f"- [{cate}](#{cate}) [Total: {cnt[cate]}]\n"

    idx = count(1)
    for cate in categories:
        markdown += f"\n\n<div id='{cate}'></div>\n\n"
        markdown += f"# {cate} [[Back]](#toc)\n\n"
        papers = []
        for item in data:
            if item["categories"][0] == cate:
                ai_data = item.get('AI', {})
                if not ai_data or not isinstance(ai_data, dict):
                    print(f"Skipping item '{item.get('title', 'Unknown')}' due to missing or invalid AI data")
                    continue

                required_fields = ['tldr', 'motivation', 'method', 'result', 'conclusion', 'future_work']
                if not all(field in ai_data for field in required_fields):
                    print(f"Skipping item '{item.get('title', 'Unknown')}' due to incomplete AI fields")
                    continue

                papers.append(
                    template.format(
                        title=item["title"],
                        authors=", ".join(item["authors"]) if isinstance(item["authors"], list) else item["authors"],
                        summary=item["summary"],
                        url=item.get('abs', ''),
                        tldr=ai_data.get('tldr', ''),
                        motivation=ai_data.get('motivation', ''),
                        method=ai_data.get('method', ''),
                        result=ai_data.get('result', ''),
                        conclusion=ai_data.get('conclusion', ''),
                        future_work=ai_data.get('future_work', ''),
                        cate=item['categories'][0],
                        idx=next(idx)
                    )
                )
        markdown += "\n\n".join(papers)

    if args.output_prefix:
        out_path = Path("data") / f"{args.output_prefix}.md"
    else:
        in_path = Path(args.data)
        out_path = in_path.with_suffix(".md")

    out_path.write_text(markdown)
    print(f"Markdown saved to {out_path}")
