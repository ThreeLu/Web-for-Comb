# Comb-Search

Daily arXiv paper tracker for combinatorics and graph theory.
Personalized paper discovery for a PhD student in extremal combinatorics,
Hamilton cycles, rainbow subgraphs, and related areas.

## Quick Start

### Daily workflow
When you say **"开始跑今天的流程"** (or "run today's workflow"):

1. **Fetch**: `python crawler/fetch.py` — pulls today's new papers from arXiv
   (categories: math.CO, math.NT, math.PR, cs.DM)
2. **Dedup**: Removes papers already seen in the last 7 days
3. **Summarize**: Claude Code reads `daily/summarization_prompt.md` and generates
   English summaries for each paper (TL;DR, Motivation, Method, Result, Conclusion, Future Work)
4. **Convert**: `python to_md/convert.py` — JSONL to Markdown
5. **Deploy**: Git commit and push → GitHub Pages auto-deploys

### Adding/removing tracked authors
Edit `config/authors.yaml` — one name per line under `authors:`.

### Adding/removing tracked keywords
Edit `config/keywords.yaml` — keywords grouped by research area.

### Site structure
- `index.html` — main paper listing with category/keyword/author filters
- `statistic.html` — keyword trends and paper statistics (Chart.js + D3.js)
- `settings.html` — manage your keyword/author preferences (saved to localStorage)

## Deployment
- **Repository**: https://github.com/ThreeLu/Web-for-Comb
- **Live site**: https://threelu.github.io/Web-for-Comb/
- **Data**: JSONL files stored in `data/`, served via GitHub raw content
