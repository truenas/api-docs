#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUGO_ROOT="$(dirname "$SCRIPT_DIR")"
STATIC_DIR="$HUGO_ROOT/static"
DATA_DIR="$HUGO_ROOT/data"
LOGFILE="$SCRIPT_DIR/cleanup_api_docs.log"

API_VERSIONS_YAML="$DATA_DIR/api_versions.yaml"
STATIC_API_YAML="$DATA_DIR/api_static_pages.yaml"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

log "Starting cleanup of TrueNAS API docs artifacts"

# Remove versioned API docs folders from static/
log "Removing versioned API docs folders from $STATIC_DIR"
shopt -s nullglob
for dir in "$STATIC_DIR"/*; do
  basename="$(basename "$dir")"
  if [[ -d "$dir" ]] && echo "$basename" | grep -Eq '^v?[0-9]+\.[0-9]+(\.[0-9]+)?$'; then
    log "Removing $dir"
    rm -rf "$dir"
  fi
done
shopt -u nullglob

# Remove generated YAML files from data/
for yaml in "$API_VERSIONS_YAML" "$STATIC_API_YAML"; do
  if [[ -f "$yaml" ]]; then
    log "Removing $yaml"
    rm -f "$yaml"
  else
    log "File $yaml does not exist, skipping"
  fi
done

# Remove any tmp_api_docs* directories in HUGO_ROOT and SCRIPT_DIR
for dir in "$HUGO_ROOT" "$SCRIPT_DIR"; do
  for tmpdir in "$dir"/tmp_api_docs*; do
    if [[ -d "$tmpdir" ]]; then
      log "Removing temp directory $tmpdir"
      rm -rf "$tmpdir"
    fi
  done
done

log "Cleanup complete."