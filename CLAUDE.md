# Comb-Search

Daily arXiv paper tracker for combinatorics and graph theory.

## How it runs

The pipeline runs **automatically every day via GitHub Actions**
(`.github/workflows/daily.yml`, cron 02:30 UTC). It also supports manual runs
(`workflow_dispatch`) and local runs.

Pipeline (`pipeline/run.sh`):

1. **fetch** (`pipeline/fetch.py`) — scrape arXiv `/list/{cat}/new` for the new
   submission ID set, then batch-fetch metadata (abstract, real submission date,
   authors, categories) via the arXiv API `id_list` endpoint (1 request per 100
   papers, with a listing fallback). → `data/{date}.jsonl` (full set, kept for dedup)
2. **dedup** (`pipeline/dedup.py`) — drop papers seen in the last 7 days
3. **match** (`pipeline/match.py`) — keep only papers hitting a tracked
   keyword/author. → `data/{date}.matched.jsonl` (gitignored intermediate).
   Runs **before** AI so we only summarize papers we keep.
4. **summarize** (`pipeline/summarize.py`) — call the LLM API for a Chinese
   structured summary per paper. → `data/{date}_ai_enhanced.jsonl`
5. **markdown** (`pipeline/to_markdown.py`) → `data/{date}.md`
6. **RSS** (`pipeline/make_feed.py`) → `feed.xml` (last 14 days of matched papers)
7. **email** (`pipeline/send_email.py`) — optional daily digest, only sends if
   `SMTP_HOST` is set (otherwise skips silently)
8. **file list + stats** → `assets/file-list.txt`, `assets/stats.json`
   (`pipeline/make_stats.py`: per-day matched/fetched counts + keyword frequency;
   powers the site's trend bar)
9. **commit** (CI also pushes)

Frontend notes: papers are sorted by relevance (author hits weighted over
keyword hits). All third-party assets (KaTeX, flatpickr, fonts) are self-hosted
under `assets/vendor/` — no external CDN, so the site loads reliably in mainland
China. Do not re-add CDN `<link>`/`<script>` tags to `index.html`.

Matching (`pipeline/match.py`) uses token-boundary regex (with an optional
trailing "s" for plurals) instead of raw substrings, and records why each paper
matched in `match_reasons: {keywords, authors}` — the frontend shows these as
chips and highlights matched keywords. Use `match.py --dry-run` to preview
what today's papers match (and which keywords never fire) before editing
`config/keywords.yaml`.

Cost guard: `MAX_PAPERS` (repo Variable) caps how many papers get summarized.
On a weekday with 0 papers fetched, the run fails loudly (`ALERT_ON_EMPTY`) so
CI notifies you that the scraper likely broke.

Tests: `uv run pytest` (also runs in CI via `.github/workflows/test.yml`).

**Output format is load-bearing.** The website reads
`data/{date}_ai_enhanced.jsonl`, expecting every original field plus a nested
`"AI": {tldr, motivation, method, result, conclusion, future_work}` object and
`matched: true`. `summarize.py` merges the AI object without dropping original
fields — never hand-write this file. (See 2026-06-04 bug: missing fields → 0
matches, empty site.)

## AI provider config

Configured via env vars (defaults to **DeepSeek**); see `.env.example`.

- **Required**: `LLM_API_KEY` (aliases: `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`)
- Optional: `LLM_BASE_URL` (default `https://api.deepseek.com`),
  `LLM_MODEL` (default `deepseek-chat`), `LLM_JSON_MODE`, `LLM_MAX_WORKERS`

In GitHub Actions: set `LLM_API_KEY` as a repo **Secret**; set
`LLM_BASE_URL` / `LLM_MODEL` as repo **Variables** to switch providers.

## Running locally

```bash
uv sync
export LLM_API_KEY=sk-...        # or put it in .env
bash pipeline/run.sh             # today; add a YYYY-MM-DD arg for a past date
git push origin main             # deploy (run.sh commits but does not push)
```

## Config

- **Keywords**: `config/keywords.yaml`
- **Authors**: `config/authors.yaml`
- Changes take effect on the next pipeline run.

## Deploy

- Repo: https://github.com/ThreeLu/Web-for-Comb (GitHub Pages serves `main`;
  data must stay on `main` since the frontend loads it via relative paths)
- Site: https://threelu.github.io/Web-for-Comb/
