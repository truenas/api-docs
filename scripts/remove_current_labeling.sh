#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUGO_ROOT="$(dirname "$SCRIPT_DIR")"
STATIC_DIR="$HUGO_ROOT/static"

echo "Scanning $STATIC_DIR for versioned HTML files..."

# Count total files first for progress indication
total_files=$(find "$STATIC_DIR" -maxdepth 2 -name "*.html" -path "*/v[0-9]*.[0-9]*/*" | wc -l)
echo "Found $total_files HTML files to process..."

# Use find with parallel processing for much better performance
if command -v parallel >/dev/null 2>&1; then
  echo "Using GNU parallel for faster processing..."
  find "$STATIC_DIR" -maxdepth 2 -name "*.html" -path "*/v[0-9]*.[0-9]*/*" -print0 | \
    parallel -0 -j $(nproc) "sed -i 's/ *(current) */ /g' {}"
else
  echo "Using find with batch processing..."
  # Batch process files in groups to reduce overhead
  find "$STATIC_DIR" -maxdepth 2 -name "*.html" -path "*/v[0-9]*.[0-9]*/*" -print0 | \
    xargs -0 -n 100 -P $(nproc) sed -i 's/ *(current) */ /g'
fi

echo "Removed '(current)' from all versioned HTML files in $STATIC_DIR."