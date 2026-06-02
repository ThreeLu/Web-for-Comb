#!/usr/bin/env python3
"""Merge AI summaries into paper JSONL."""
import json, sys
from pathlib import Path
from ai_summaries import SUMMARIES

INPUT = sys.argv[1] if len(sys.argv) > 1 else "data/2026-06-02.jsonl"
OUTPUT = INPUT.replace(".jsonl", "_ai_enhanced.jsonl")

with open(INPUT) as f:
    papers = [json.loads(line) for line in f if line.strip()]

has_ai = 0
for p in papers:
    pid = p["id"]
    if pid in SUMMARIES:
        p["AI"] = SUMMARIES[pid]
        has_ai += 1
    else:
        # Placeholder — real workflow fills these via Claude Code
        abstract = p.get("summary", "")
        p["AI"] = {
            "tldr": abstract[:250] if abstract else "(pending AI summary)",
            "motivation": "",
            "method": "",
            "result": "",
            "conclusion": "",
            "future_work": ""
        }

with open(OUTPUT, "w") as f:
    for p in papers:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

print(f"Merged: {has_ai}/{len(papers)} papers with full AI summaries")
print(f"Output: {OUTPUT}")
