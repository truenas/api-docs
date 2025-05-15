#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUGO_ROOT="$(dirname "$SCRIPT_DIR")"
STATIC_DIR="$HUGO_ROOT/static"

echo "Scanning $STATIC_DIR for versioned HTML files..."

shopt -s nullglob
for version_dir in "$STATIC_DIR"/v*; do
  # Only process directories matching v##.## or v##.##.##
  if [[ -d "$version_dir" && "$version_dir" =~ /v[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]; then
    for html_file in "$version_dir"/*.html; do
      [ -f "$html_file" ] || continue
      sed -i.bak 's/ *(current) */ /g' "$html_file"
      rm -f "${html_file}.bak"
    done
  fi
done
shopt -u nullglob

echo "Removed '(current)' from all versioned HTML files in $STATIC_DIR."