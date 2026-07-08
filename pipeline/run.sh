#!/bin/bash
# ============================================================
# Comb-Search Daily Pipeline (fully automated)
#
#   fetch -> dedup -> match -> AI summarize -> markdown -> file list -> commit
#
# Matching runs BEFORE summarization, so we only pay the LLM for papers we keep.
# The AI step needs an API key (default provider: DeepSeek). See .env.example.
#
# Usage:
#   bash pipeline/run.sh              # today (UTC)
#   bash pipeline/run.sh 2026-06-20   # a specific date
#
# Env:
#   PYTHON     python launcher (default: python3; CI sets "uv run python")
#   SKIP_GIT   set to 1 to skip the commit step
#   LLM_API_KEY / LLM_BASE_URL / LLM_MODEL   see pipeline/summarize.py
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

PY="${PYTHON:-python3}"
TODAY="${1:-$(date -u "+%Y-%m-%d")}"
DATA_FILE="data/${TODAY}.jsonl"
MATCHED_FILE="data/${TODAY}.matched.jsonl"
AI_FILE="data/${TODAY}_ai_enhanced.jsonl"

echo "=============================================="
echo " Comb-Search Daily Pipeline — $TODAY"
echo "=============================================="

# ── Step 1: Fetch ─────────────────────────────────────────
echo ""
echo "--- Step 1: Fetching arXiv papers ---"
$PY pipeline/fetch.py --date "$TODAY" --output-dir data
COUNT=$(wc -l < "$DATA_FILE" 2>/dev/null | tr -d ' ' || echo 0)
echo "Papers fetched: $COUNT"
if [ "$COUNT" -eq 0 ]; then
    # 0 papers on a weekday almost always means the scraper broke (arXiv
    # redesign, network). Fail loudly so CI notifies. arXiv rarely announces
    # on weekends, so a weekend 0 is expected. Toggle with ALERT_ON_EMPTY=0.
    DOW=$($PY -c "import datetime;print(datetime.date.fromisoformat('$TODAY').isoweekday())")
    if [ "${ALERT_ON_EMPTY:-1}" = "1" ] && [ "$DOW" -le 5 ]; then
        echo "ALERT: 0 papers fetched on a weekday — arXiv scraper may be broken." >&2
        exit 1
    fi
    echo "No new papers on arXiv today. Nothing to do."
    exit 0
fi

# ── Step 2: Dedup ─────────────────────────────────────────
echo ""
echo "--- Step 2: Deduplication ---"
$PY pipeline/dedup.py --date "$TODAY" --history-days 7
if [ ! -f "$DATA_FILE" ]; then
    echo "All $COUNT papers already seen this week. Nothing new."
    exit 0
fi
DEDUP_COUNT=$(wc -l < "$DATA_FILE" 2>/dev/null | tr -d ' ')
echo "Papers after dedup: $DEDUP_COUNT"

# ── Step 3: Keyword + author matching ─────────────────────
echo ""
echo "--- Step 3: Matching keywords & authors ---"
$PY pipeline/match.py --data "$DATA_FILE" --output "$MATCHED_FILE"
MATCH_COUNT=$(wc -l < "$MATCHED_FILE" 2>/dev/null | tr -d ' ' || echo 0)
echo "Matched papers: $MATCH_COUNT"

if [ "$MATCH_COUNT" -eq 0 ]; then
    echo "No papers matched today's keywords/authors."
    rm -f "$MATCHED_FILE"
    # Still commit the raw fetch so dedup history stays complete.
    COMMIT_MSG="daily: $TODAY (0 matched, $DEDUP_COUNT scanned)"
else
    # ── Step 4: AI summarization ──────────────────────────
    echo ""
    echo "--- Step 4: AI summarization ---"
    $PY pipeline/summarize.py --input "$MATCHED_FILE" --output "$AI_FILE" \
        --limit "${MAX_PAPERS:-0}"

    # ── Step 5: Markdown ──────────────────────────────────
    echo ""
    echo "--- Step 5: Converting to Markdown ---"
    $PY pipeline/to_markdown.py --data "$AI_FILE" --output-prefix "$TODAY"

    rm -f "$MATCHED_FILE"
    COMMIT_MSG="daily: $TODAY ($MATCH_COUNT matched papers)"
fi

# ── Step 5b: RSS feed ─────────────────────────────────────
echo ""
echo "--- Step 5b: Building RSS feed ---"
$PY pipeline/make_feed.py --data-dir data --output feed.xml --days 14 || \
    echo "(feed build skipped)"

# ── Step 5c: Optional email digest (skips unless SMTP_HOST is set) ─────────
if [ -f "$AI_FILE" ]; then
    echo ""
    echo "--- Step 5c: Email digest (optional) ---"
    $PY pipeline/send_email.py --data "$AI_FILE" --date "$TODAY" || \
        echo "(email step failed — continuing)"
fi

# ── Step 6: File list ─────────────────────────────────────
echo ""
echo "--- Step 6: Updating file list + stats ---"
ls data/*_ai_enhanced.jsonl 2>/dev/null | sed 's|data/||' > assets/file-list.txt || true
$PY pipeline/make_stats.py --data-dir data --output assets/stats.json || \
    echo "(stats build skipped)"
echo "Updated assets/file-list.txt and assets/stats.json"

# ── Step 7: Commit ────────────────────────────────────────
if [ "${SKIP_GIT:-0}" = "1" ]; then
    echo ""
    echo "SKIP_GIT=1 — leaving changes uncommitted."
    exit 0
fi

echo ""
echo "--- Step 7: Commit ---"
git add data/ assets/file-list.txt assets/stats.json feed.xml 2>/dev/null || \
    git add data/ assets/file-list.txt
if git diff --cached --quiet; then
    echo "No changes to commit."
else
    git commit -m "$COMMIT_MSG"
    echo "Committed: $COMMIT_MSG"
fi
