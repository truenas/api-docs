#!/bin/bash
#
# Process existing API documentation in the public directory to add pagefind attributes.
# This script is useful for adding pagefind attributes to docs that have already been
# pulled and built, without needing to re-pull them from containers.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUGO_ROOT="$(dirname "$SCRIPT_DIR")"
PUBLIC_DIR="$HUGO_ROOT/public"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Processing existing API documentation in $PUBLIC_DIR"

# Find all version directories in public
version_dirs=$(find "$PUBLIC_DIR" -maxdepth 1 -type d -name 'v*.*' | sort -V)

if [[ -z "$version_dirs" ]]; then
  log "No version directories found in $PUBLIC_DIR"
  exit 1
fi

for version_dir in $version_dirs; do
  version=$(basename "$version_dir")
  log "Processing $version"
  "$SCRIPT_DIR/add_pagefind_attributes.sh" "$version_dir" "api" "TrueNAS API"
done

log "Done! You can now run 'npx pagefind --site public' to rebuild the search index."
