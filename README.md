# Comb-Search 🔬

Daily arXiv paper tracker for combinatorics and graph theory.

A personalized academic website that fetches new papers from arXiv every day
in **math.CO, math.NT, math.PR, cs.DM**, tracks ~50 research keywords
(absorption method, Hamilton cycles, rainbow subgraphs, extremal combinatorics,
Ramsey theory, random graphs, combinatorial designs, etc.), and monitors
publications from ~45 leading researchers in the field.

## Features

- **Fully automated** — Runs every day on GitHub Actions (cron), no manual steps
- **Daily arXiv crawling** — Automatically fetches new papers in combinatorics
- **AI summarization** — Each matched paper gets a structured Chinese summary
  (TL;DR, Motivation, Method, Result, Conclusion, Future Work) via an
  OpenAI-compatible API (DeepSeek by default, configurable)
- **Personalized filtering** — Keyword/author matching before summarization
- **LaTeX rendering** — All mathematical notation rendered with KaTeX
- **Statistics dashboard** — Keyword trends and paper analytics

## Setup

The daily workflow needs one secret. In the GitHub repo settings:

- **Secrets → Actions**: add `LLM_API_KEY` (your DeepSeek/OpenAI key)
- **Variables → Actions** (optional): `LLM_BASE_URL`, `LLM_MODEL` to switch
  providers

See `.env.example` and `CLAUDE.md` for local runs and full config.

## Live Site

👉 **[threelu.github.io/Web-for-Comb](https://threelu.github.io/Web-for-Comb/)**

## Author

A PhD student in graph theory and combinatorics.

## License

MIT
