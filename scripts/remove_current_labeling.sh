#!/bin/bash

set -euo pipefail

# Reuse logic from pull_api_docs.sh to find STATIC_DIR
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUGO_ROOT="$(dirname "$SCRIPT_DIR")"
STATIC_DIR="$HUGO_ROOT/static"

echo "Scanning $STATIC_DIR for versioned HTML files..."

# Find all versioned directories (e.g., v25.10.0)
find "$STATIC_DIR" -maxdepth 1 -type d -regextype posix-extended -regex '.*/v[0-9]+\.[0-9]+(\.[0-9]+)?'
  # Find all HTML files in the versioned directory
  find "$version_dir" -type f -name '*.html' | while read -r html_file; do
    # Remove all occurrences of '(current)' (with optional leading/trailing spaces)
    sed -i.bak 's/ *(current) */ /g' "$html_file"
    # Remove backup file created by sed (optional)
    rm -f "${html_file}.bak"
  done
done

echo "Removed '(current)' from all versioned HTML files in $STATIC_DIR."