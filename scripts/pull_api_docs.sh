#!/bin/bash

set -euo pipefail

LOGFILE="$(dirname "$0")/pull_api_docs.log"
exec > >(tee -a "$LOGFILE") 2>&1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUGO_ROOT="$(dirname "$SCRIPT_DIR")"
STATIC_DIR="$HUGO_ROOT/static"
TMP_DIR="$(mktemp -d "$HUGO_ROOT/tmp_api_docs.XXXXXX")"
DATA_DIR="$HUGO_ROOT/data"
API_VERSIONS_YAML="$DATA_DIR/api_versions.yaml"
STATIC_API_YAML="$DATA_DIR/api_static_pages.yaml"
DOCKER_IMAGE="ghcr.io/truenas/middleware:master"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

cleanup() {
  if [[ -n "${CONTAINER_ID:-}" ]]; then
    docker rm -f "$CONTAINER_ID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

log "Starting TrueNAS API docs pull"

log "Pulling Docker image: $DOCKER_IMAGE"
docker pull "$DOCKER_IMAGE"

log "Creating Docker container"
CONTAINER_ID=$(docker create "$DOCKER_IMAGE" sleep 60)
if [[ -z "$CONTAINER_ID" ]]; then
  log "Failed to create Docker container. Exiting."
  exit 1
fi

log "Copying docs from container"
docker cp "$CONTAINER_ID":/usr/share/middlewared/docs "$TMP_DIR/"

log "Removing old versioned API docs from $STATIC_DIR"
find "$STATIC_DIR" -maxdepth 1 -type d -regextype posix-extended -regex '.*/v?[0-9]+\.[0-9]+' -exec rm -rf {} +

log "Copying new docs to $STATIC_DIR"
cp -r "$TMP_DIR/docs/"* "$STATIC_DIR/"

log "Generating $API_VERSIONS_YAML"
mkdir -p "$DATA_DIR"
find "$STATIC_DIR" -maxdepth 1 -type d -name 'v*.*' | sed "s|$STATIC_DIR/||" | sort -V | awk '{print "- "$0}' > "$API_VERSIONS_YAML"

log "Generating $STATIC_API_YAML"
: > "$STATIC_API_YAML"
find "$STATIC_DIR" -maxdepth 1 -type d -name 'v*.*' | while read -r dir; do
  find "$dir" -type f -name '*.html' | sort | while read -r file; do
    echo "- url: ${file#$STATIC_DIR/}" >> "$STATIC_API_YAML"
  done
done

log "TrueNAS API docs have been updated in $STATIC_DIR"