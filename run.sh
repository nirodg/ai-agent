#!/usr/bin/env bash
# run.sh — Start the AI Sales Enrichment Agent (macOS / Linux)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtualenv if present and not already active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d ".venv" ]; then
        echo "🔧 Activating .venv…"
        source .venv/bin/activate
    else
        echo "⚠️  No .venv found. Run: python setup.py"
        exit 1
    fi
fi

# Check .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env not found. Run: python setup.py"
    exit 1
fi

echo "🚀 Starting AI Sales Enrichment Agent…"
echo "   URL: http://localhost:8501"
echo "   Press Ctrl+C to stop."
echo ""

python -m streamlit run main.py \
    --server.port 8501 \
    --server.headless false \
    --browser.gatherUsageStats false