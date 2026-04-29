#!/bin/bash
# Atomically promote data_next/ -> data/ while archiving current data/ -> data_old/
# Usage:
#   ./swap_data.sh              # promote data_next -> data
#   ./swap_data.sh --dry-run    # preview what would happen
#   ./swap_data.sh --rollback   # restore data_old -> data

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
DATA="$ROOT/data"
NEXT="$ROOT/data_next"
OLD="$ROOT/data_old"

dry_run=false
rollback=false

for arg in "$@"; do
  case $arg in
    --dry-run) dry_run=true ;;
    --rollback) rollback=true ;;
  esac
done

if $rollback; then
  if [ ! -d "$OLD" ]; then
    echo "ERROR: $OLD does not exist, nothing to roll back to."
    exit 1
  fi
  echo "Rolling back: $OLD -> $DATA"
  if ! $dry_run; then
    [ -d "$DATA" ] && mv "$DATA" "${DATA}_rolled_$(date +%Y%m%d_%H%M%S)"
    mv "$OLD" "$DATA"
    echo "Rollback complete."
  else
    echo "[DRY RUN] Would move $DATA -> ${DATA}_rolled_* and $OLD -> $DATA"
  fi
  exit 0
fi

# --- Promote data_next -> data ---
if [ ! -d "$NEXT" ]; then
  echo "ERROR: $NEXT does not exist. Run the pipeline first:"
  echo "  DATA_DIR_PATH=data_next python main.py scrape-all --mode full"
  exit 1
fi

# Quick sanity check: next must have a chroma dir and tiger_brain.json
if [ ! -f "$NEXT/tiger_brain.json" ]; then
  echo "ERROR: $NEXT/tiger_brain.json missing — pipeline may not be complete."
  echo "Check $NEXT/research_cards/ count before swapping."
  exit 1
fi

echo "=== Swap plan ==="
echo "  ARCHIVE: $DATA   -> $OLD"
echo "  PROMOTE: $NEXT   -> $DATA"
echo ""

CARDS=$(ls "$NEXT/research_cards/"*.json 2>/dev/null | wc -l)
NODES=$(python3 -c "import json; g=json.load(open('$NEXT/tiger_brain.json')); print(len(g.get('nodes',[])))" 2>/dev/null || echo "?")
echo "  data_next stats: $CARDS research cards, $NODES graph nodes"
echo ""

if $dry_run; then
  echo "[DRY RUN] No changes made."
  exit 0
fi

read -p "Proceed with swap? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Aborted."
  exit 1
fi

[ -d "$OLD" ] && rm -rf "$OLD"
mv "$DATA" "$OLD"
mv "$NEXT" "$DATA"

echo ""
echo "Swap complete."
echo "  Live data: $DATA ($CARDS cards, $NODES nodes)"
echo "  Archived:  $OLD"
echo ""
echo "Restart the API to pick up new data:"
echo "  pkill -f 'uvicorn api:app' ; uvicorn api:app --host 0.0.0.0 --port 8000 &"
