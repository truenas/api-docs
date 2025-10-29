#!/bin/bash
# Add pagefind data attributes to Sphinx-generated API documentation HTML files.
# This script uses pure bash/sed to post-process HTML files for pagefind indexing.
#

set -euo pipefail

usage() {
  echo "Usage: $0 <directory> [site_key] [site_name]"
  echo "Example: $0 static/v25.04 api 'TrueNAS API'"
  exit 1
}

if [[ $# -lt 1 ]]; then
  usage
fi

DIRECTORY="$1"
SITE_KEY="${2:-api}"
SITE_NAME="${3:-TrueNAS API}"

if [[ ! -d "$DIRECTORY" ]]; then
  echo "Error: Directory '$DIRECTORY' does not exist"
  exit 1
fi

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

process_html_file() {
  local file="$1"
  local site_key="$2"
  local site_name="$3"
  local version="$4"

  # Skip certain files
  local filename=$(basename "$file")
  if [[ "$filename" == "search.html" || "$filename" == "genindex.html" || "$filename" == "py-modindex.html" ]]; then
    return 0
  fi

  # Check if file already has pagefind attributes (idempotency check)
  if grep -q "data-pagefind-body" "$file"; then
    return 0
  fi

  # Create a temporary file
  local tmpfile="${file}.tmp"

  # Extract title from <title> tag and clean it up (remove " — TrueNAS API..." or " &#8212; TrueNAS API..." suffix)
  local title=$(grep -o '<title>[^<]*</title>' "$file" | sed 's/<title>//;s/<\/title>//;s/ —.*$//;s/ &#8212;.*$//' | head -1)

  # If no title found, try h1
  if [[ -z "$title" ]]; then
    title=$(grep -o '<h1>[^<]*</h1>' "$file" | sed 's/<h1>//;s/<\/h1>//;s/<a class.*//;s/¶//' | head -1)
  fi

  # Default title if still empty
  if [[ -z "$title" ]]; then
    title="Untitled"
  fi

  # Escape special characters in title for use in sed
  title=$(echo "$title" | sed 's/[&/\]/\\&/g')

  # Build separate metadata attributes (pagefind requires separate attributes, not comma-separated)
  local title_meta="title:${title}"
  local version_attr=""
  if [[ -n "$version" ]]; then
    version_attr=" data-pagefind-meta=\"version:${version}\""
  fi

  # Process the file with sed
  # 1. Add data-pagefind-body and metadata to <div class="body">
  # 2. Add data-pagefind-ignore to navigation elements
  sed -e "s|<div class=\"body\"|<div class=\"body\" data-pagefind-body data-pagefind-meta=\"${title_meta}\"${version_attr}|" \
      -e "s|<nav |<nav data-pagefind-ignore |g" \
      -e "s|<div class=\"sphinxsidebar\"|<div class=\"sphinxsidebar\" data-pagefind-ignore|g" \
      -e "s|<div class=\"related\"|<div class=\"related\" data-pagefind-ignore|g" \
      -e "s|<footer |<footer data-pagefind-ignore |g" \
      -e "s|<form action=\"search.html\"|<form action=\"search.html\" data-pagefind-ignore|g" \
      -e "s|<form class=\"form-inline\" action=\"search.html\"|<form class=\"form-inline\" action=\"search.html\" data-pagefind-ignore|g" \
      -e "s|<form class=\"form search\" action=\"search.html\"|<form class=\"form search\" action=\"search.html\" data-pagefind-ignore|g" \
      "$file" > "$tmpfile"

  # Replace original file with processed version
  mv "$tmpfile" "$file"
}

export -f process_html_file
export -f log

log "Processing HTML files in: $DIRECTORY"
log "Site Key: $SITE_KEY"
log "Site Name: $SITE_NAME"

# Extract version from directory path (e.g., "v25.04" from "/path/to/v25.04")
VERSION=""
if [[ "$DIRECTORY" =~ (v[0-9]+\.[0-9]+) ]]; then
  VERSION="${BASH_REMATCH[1]}"
  log "Detected Version: $VERSION"
else
  log "No version detected in path"
fi

log "----------------------------------------"

# Find all HTML files and process them
files_processed=0
find "$DIRECTORY" -type f -name "*.html" | while read -r html_file; do
  filename=$(basename "$html_file")

  # Skip index files that are just redirects
  if [[ "$filename" == "index.html" ]] && grep -q "window.location.replace" "$html_file" 2>/dev/null; then
    continue
  fi

  log "Processing: $html_file"
  process_html_file "$html_file" "$SITE_KEY" "$SITE_NAME" "$VERSION"
  ((files_processed++)) || true
done

log "----------------------------------------"
log "Processing complete. Files processed: $files_processed"
