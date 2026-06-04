# Comb-Search

Daily arXiv paper tracker for combinatorics and graph theory.

## Daily workflow

When you say **"开始跑今天的流程"**:

1. Run `bash daily/run.sh` — fetches papers, deduplicates, matches keywords
2. Read `daily/summarization_prompt.md`
3. For each paper in `data/{today}.jsonl`, generate Chinese summary (TL;DR,
   Motivation, Method, Result, Conclusion, Future Work). **CRITICAL**: Use a
   Python script to merge — read original `data/{today}.jsonl`, add `"AI": {...}`
   nested object to each paper, write to `data/{today}_ai_enhanced.jsonl`.
   NEVER write the file manually without original fields (title, summary, authors
   etc.) — match.py needs them for keyword matching. See 2026-06-04 bug for what
   happens if you get this wrong (0 matches, empty site).
4. Rerun `bash daily/run.sh` to complete matching + markdown + file list
5. `git push origin main` to deploy

## Config

- **Keywords**: `config/keywords.yaml` — edit to add/remove
- **Authors**: `config/authors.yaml` — edit to add/remove
- Changes take effect next time you run the pipeline

## Deploy

- Repo: https://github.com/ThreeLu/Web-for-Comb
- Site: https://threelu.github.io/Web-for-Comb/
