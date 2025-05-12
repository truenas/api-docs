#!/bin/bash

LOGFILE="$(dirname "$0")/pull_api_docs.log"
exec > "$LOGFILE" 2>&1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUGO_ROOT="$(dirname "$SCRIPT_DIR")"
STATIC_DIR="$HUGO_ROOT/static"
TMP_DIR="$HUGO_ROOT/tmp_api_docs"
DATA_DIR="$HUGO_ROOT/data"
API_VERSIONS_JSON="$DATA_DIR/api_versions.json"

echo "Starting TrueNAS API docs pull at $(date)"

docker pull ghcr.io/truenas/middleware:master

# Start a container in the background with a harmless command
CONTAINER_ID=$(docker create ghcr.io/truenas/middleware:master sleep 60)

# Check if container was created
if [ -z "$CONTAINER_ID" ]; then
  echo "Failed to create Docker container. Exiting."
  exit 1
fi

# Copy docs from the container to the temp dir
mkdir -p "$TMP_DIR"
docker cp "$CONTAINER_ID":/usr/share/middlewared/docs "$TMP_DIR/"

# Clean up the container
docker rm "$CONTAINER_ID"

# Remove only old versioned API docs folders (e.g., 25.04, 25.10, v25.04, v25.10, etc.)
find "$STATIC_DIR/" -maxdepth 1 -type d -regex '.*/v?[0-9]+\.[0-9]+' -exec rm -rf {} +

# Copy new versioned docs into static/
cp -r "$TMP_DIR/docs/"* "$STATIC_DIR/"

# Generate api_versions.yaml for Hugo (expects version folders like v25.04, v25.10)
mkdir -p "$DATA_DIR"
cd "$STATIC_DIR"
find . -maxdepth 1 -type d -name 'v*.*' | sed 's|^\./||' | sort -V | awk '{print "- "$0}' > "$DATA_DIR/api_versions.yaml"

# Generate api_static_pages.yaml for Hugo sitemap
STATIC_API_YAML="$DATA_DIR/api_static_pages.yaml"
cd "$STATIC_DIR"
echo "" > "$STATIC_API_YAML"
for dir in v*.*; do
  if [ -d "$dir" ]; then
    find "$dir" -type f -name '*.html' | sort | while read -r file; do
      echo "- url: ${file}" >> "$STATIC_API_YAML"
    done
  fi
done

# Clean up temp directories
rm -rf "$TMP_DIR"
rm -rf "$SCRIPT_DIR/tmp_api_docs"*

echo "TrueNAS API docs have been updated in static/ at $(date)"