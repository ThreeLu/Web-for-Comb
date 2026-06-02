#!/bin/bash
# ============================================================
# Comb-Search Daily Pipeline
# Run this to fetch, dedup, summarize, and publish papers.
#
# Usage:
#   Claude Code:  "开始跑今天的流程"
#   Codex CLI:    "codex run daily/run.sh"
#   Manual:       bash daily/run.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

TODAY=$(date -u "+%Y-%m-%d")
DATA_FILE="data/${TODAY}.jsonl"
AI_FILE="data/${TODAY}_ai_enhanced.jsonl"

echo "╔══════════════════════════════════════════════╗"
echo "║    Comb-Search Daily Pipeline               ║"
echo "║    Date: $TODAY                       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Step 1: Fetch papers ──────────────────────────────────
echo "━━━ Step 1: Fetching arXiv papers ━━━"
python crawler/fetch.py --date "$TODAY" --output-dir data
COUNT=$(cat "$DATA_FILE" 2>/dev/null | wc -l | tr -d ' ')
echo "Papers fetched: $COUNT"

if [ "$COUNT" -eq 0 ]; then
    echo ""
    echo "🎉  No new papers on arXiv today!"
    echo "   (Weekends and holidays — arXiv doesn't post new papers)"
    echo "   Enjoy a peaceful day. ✨"
    exit 0
fi

# ── Step 2: Dedup ─────────────────────────────────────────
echo ""
echo "━━━ Step 2: Deduplication ━━━"
python daily/dedup.py --date "$TODAY" --history-days 7
DEDUP_COUNT=$(cat "$DATA_FILE" 2>/dev/null | wc -l | tr -d ' ')
echo "Papers after dedup: $DEDUP_COUNT"

if [ "$DEDUP_COUNT" -eq 0 ]; then
    echo ""
    echo "📋  All $COUNT papers are duplicates from recent days."
    echo "   Nothing new to process. Have a great day! 🌿"
    rm -f "$DATA_FILE"
    exit 0
fi

# ── Step 3: AI Summarization ──────────────────────────────
echo ""
echo "━━━ Step 3: AI Summarization ━━━"
echo "📝  AI summarization is handled by Claude Code / Codex."
echo ""
echo "   The prompt template is at: daily/summarization_prompt.md"
echo "   Papers to summarize:       $DATA_FILE  ($DEDUP_COUNT papers)"
echo "   Output should go to:       $AI_FILE"
echo ""
echo "   >>> Claude/Codex: please read the prompt and generate summaries. <<<"
echo ""

# ── Step 4: Convert to Markdown ──────────────────────────
# (Uncommented if AI file already exists from a previous run)
if [ -f "$AI_FILE" ]; then
    echo "━━━ Step 4: Converting to Markdown ━━━"
    python to_md/convert.py --data "$AI_FILE" --output-prefix "$TODAY"
    echo "Markdown saved to data/${TODAY}.md"
else
    echo "⏭️  Step 4: Skipped (AI file not found — run AI summarization first)"
fi

# ── Step 5: Update file list ──────────────────────────────
echo ""
echo "━━━ Step 5: Updating file list ━━━"
ls data/*.jsonl 2>/dev/null | sed 's|data/||' > assets/file-list.txt
echo "Updated assets/file-list.txt"

# ── Step 6: Git push ──────────────────────────────────────
echo ""
echo "━━━ Step 6: Git commit & push ━━━"
if git diff --quiet && git diff --cached --quiet; then
    git add data/ assets/file-list.txt
    git commit -m "daily: $TODAY papers ($DEDUP_COUNT papers)"
    echo "Committed changes."
fi

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║    Pipeline complete!                        ║"
echo "║    Next: git push to deploy to GitHub Pages  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "To push:  git push origin main"
