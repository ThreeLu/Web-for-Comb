#!/bin/bash
# ============================================================
# Comb-Search Daily Pipeline
#
# Usage:
#   In Claude Code:  "开始跑今天的流程"
#   In Codex CLI:    codex run daily/run.sh
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

# ── Step 1: Fetch ────────────────────────────────────────
echo "━━━ Step 1: Fetching arXiv papers ━━━"
python3 crawler/fetch.py --date "$TODAY" --output-dir data
COUNT=$(wc -l < "$DATA_FILE" 2>/dev/null | tr -d ' ')
echo "Papers fetched: $COUNT"

if [ "$COUNT" -eq 0 ]; then
    echo ""
    echo "🎉  No new papers on arXiv today. Enjoy the quiet. ✨"
    exit 0
fi

# ── Step 2: Dedup ─────────────────────────────────────────
echo ""
echo "━━━ Step 2: Deduplication ━━━"
python3 daily/dedup.py --date "$TODAY" --history-days 7
if [ ! -f "$DATA_FILE" ]; then
    echo ""
    echo "📋  All $COUNT papers already seen this week. Nothing new. 🌿"
    exit 0
fi
DEDUP_COUNT=$(wc -l < "$DATA_FILE" 2>/dev/null | tr -d ' ')
echo "Papers after dedup: $DEDUP_COUNT"

# ── Step 3: AI Summarization ──────────────────────────────
echo ""
echo "━━━ Step 3: AI Summarization ━━━"
echo "📝  This step is handled by Claude Code / Codex."
echo "    Prompt template: daily/summarization_prompt.md"
echo "    Input:           $DATA_FILE  ($DEDUP_COUNT papers)"
echo "    Output:          $AI_FILE"
echo ""

# ── Step 4: Keyword + Author Matching ─────────────────────
if [ -f "$AI_FILE" ]; then
    echo "━━━ Step 4: Matching against keywords & authors ━━━"
    python3 daily/match.py --data "$AI_FILE"
else
    echo "⏭️  Step 4 skipped (AI file not yet generated)"
fi

# ── Step 5: Markdown ──────────────────────────────────────
if [ -f "$AI_FILE" ]; then
    echo ""
    echo "━━━ Step 5: Converting to Markdown ━━━"
    python3 to_md/convert.py --data "$AI_FILE" --output-prefix "$TODAY"
else
    echo "⏭️  Step 5 skipped"
fi

# ── Step 6: File list ─────────────────────────────────────
echo ""
echo "━━━ Step 6: Updating file list ━━━"
ls data/*.jsonl 2>/dev/null | sed 's|data/||' > assets/file-list.txt
echo "Updated"

# ── Step 7: Git ───────────────────────────────────────────
echo ""
echo "━━━ Step 7: Commit & push ━━━"
if ! git diff --quiet -- data/ assets/file-list.txt 2>/dev/null || \
   ! git diff --cached --quiet 2>/dev/null; then
    git add data/ assets/file-list.txt
    git commit -m "daily: $TODAY ($DEDUP_COUNT papers)"
    echo "Committed."
else
    echo "No changes to commit."
fi

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Run 'git push origin main' to deploy.      ║"
echo "╚══════════════════════════════════════════════╝"
