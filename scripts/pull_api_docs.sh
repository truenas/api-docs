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
    log "Cleanup: Removing container $CONTAINER_ID"
    docker rm -f "$CONTAINER_ID" >/dev/null 2>&1 || true
    unset CONTAINER_ID
  fi
  if [[ -d "$TMP_DIR" ]]; then
    log "Cleanup: Removing temp directory $TMP_DIR"
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

log "Starting TrueNAS API docs pull"

log "Cleaning up old containers for $DOCKER_IMAGE"
docker ps -a --filter "ancestor=$DOCKER_IMAGE" --format '{{.ID}}' | xargs -r docker rm -f

log "Cleaning up dangling Docker images"
docker image prune -f

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

log "Removing container $CONTAINER_ID"
docker rm -f "$CONTAINER_ID" >/dev/null 2>&1 || true
unset CONTAINER_ID

log "Removing Docker image $DOCKER_IMAGE"
docker rmi "$DOCKER_IMAGE" || true

log "Removing old versioned API docs from $STATIC_DIR"
find "$STATIC_DIR" -maxdepth 1 -type d -regextype posix-extended -regex '.*/v?[0-9]+\.[0-9]+' -exec rm -rf {} +

log "Copying new docs to $STATIC_DIR"
cp -r "$TMP_DIR/docs/"* "$STATIC_DIR/"

log "Organizing docs into major version structure"
# Function to compare semantic versions
version_greater_than() {
  local ver1="$1"
  local ver2="$2"
  # Remove 'v' prefix if present
  ver1="${ver1#v}"
  ver2="${ver2#v}"
  
  # Use sort -V to compare versions, check if ver1 comes after ver2
  [ "$(printf '%s\n%s\n' "$ver1" "$ver2" | sort -V | tail -1)" = "$ver1" ] && [ "$ver1" != "$ver2" ]
}

# Extract major version from full version (e.g., v25.04.2 -> v25.04)
get_major_version() {
  local full_version="$1"
  echo "$full_version" | sed -E 's/^(v[0-9]+\.[0-9]+)(\.|$).*/\1/'
}

# Collect all version directories and organize by major version
declare -A major_versions_map
declare -A minor_versions_for_redirect

# Find all version directories
for version_dir in $(find "$STATIC_DIR" -maxdepth 1 -type d -name 'v*.*' | sed "s|$STATIC_DIR/||" | sort -V); do
  major_version=$(get_major_version "$version_dir")
  
  # Track this version for potential redirect creation
  minor_versions_for_redirect["$version_dir"]="$major_version"
  
  # Keep the latest version for each major version
  if [[ -z "${major_versions_map[$major_version]:-}" ]]; then
    major_versions_map["$major_version"]="$version_dir"
  else
    current_latest="${major_versions_map[$major_version]}"
    if version_greater_than "$version_dir" "$current_latest"; then
      major_versions_map["$major_version"]="$version_dir"
    fi
  fi
done

# Create major version directories with latest content
for major_version in "${!major_versions_map[@]}"; do
  latest_minor="${major_versions_map[$major_version]}"
  
  log "Creating major version directory $major_version with content from $latest_minor"
  
  # Only proceed if the major version is different from the latest minor version
  if [[ "$major_version" != "$latest_minor" ]]; then
    # Copy the latest minor version content to major version directory
    cp -r "$STATIC_DIR/$latest_minor" "$STATIC_DIR/$major_version"
  fi
done

log "Generating $API_VERSIONS_YAML with new structure"
mkdir -p "$DATA_DIR"
{
  echo "versions:"
  for major_version in $(printf '%s\n' "${!major_versions_map[@]}" | sort -V); do
    latest_minor="${major_versions_map[$major_version]}"
    echo "- major: \"$major_version\""
    echo "  latest: \"$latest_minor\""
    echo "  full_display: \"$latest_minor\""
  done
} > "$API_VERSIONS_YAML"

log "Creating HTML redirect pages for minor versions"
for version_dir in "${!minor_versions_for_redirect[@]}"; do
  major_version="${minor_versions_for_redirect[$version_dir]}"
  
  # Only create redirect if this version is NOT the canonical major version
  if [[ "$version_dir" != "$major_version" ]]; then
    log "Creating redirect page for $version_dir -> $major_version"
    
    # Create the redirect HTML page
    cat > "$STATIC_DIR/$version_dir/index.html" << EOF
<!DOCTYPE html>
<html>
<head>
  <title>TrueNAS API $version_dir - Redirecting</title>
  <meta http-equiv="refresh" content="0; url=/$major_version/">
  <script>window.location.replace("/$major_version/")</script>
</head>
<body>
  <p>Redirecting to <a href="/$major_version/">TrueNAS API $major_version</a>...</p>
</body>
</html>
EOF
  fi
done

log "Updating version dropdowns in HTML files to show only major versions"
# Generate the dropdown options HTML for major versions only
dropdown_options=""
for major_version in $(printf '%s\n' "${!major_versions_map[@]}" | sort -V -r); do
  latest_minor="${major_versions_map[$major_version]}"
  if [[ "$major_version" == "$latest_minor" ]]; then
    # This is already a major version directory
    dropdown_options+="<option value=\"$major_version\">$major_version</option>"
  else
    # Use major version in dropdown but show full version text
    dropdown_options+="<option value=\"$major_version\">$latest_minor</option>"
  fi
done

# Update dropdown in all HTML files in major version directories
for major_version in $(printf '%s\n' "${!major_versions_map[@]}" | sort -V); do
  if [[ -d "$STATIC_DIR/$major_version" ]]; then
    log "Updating dropdowns in $major_version HTML files"
    find "$STATIC_DIR/$major_version" -name "*.html" -type f | while read -r html_file; do
      # Extract current selected version from the file
      selected_version=""
      if grep -q "selected.*$major_version" "$html_file"; then
        selected_version="$major_version"
      fi
      
      # Replace the dropdown options with major version options
      if [[ -n "$selected_version" ]]; then
        # Add selected attribute to the current version
        updated_dropdown_options=$(echo "$dropdown_options" | sed "s|<option value=\"$selected_version\">|<option value=\"$selected_version\" selected>|")
      else
        updated_dropdown_options="$dropdown_options"
      fi
      
      # Replace the entire select element 
      sed -i.bak "s|<select class=\"form-control\" onchange=\"navigateToVersion(this.value);\">.*</select>|<select class=\"form-control\" onchange=\"navigateToVersion(this.value);\">$updated_dropdown_options</select>|g" "$html_file"
      rm -f "${html_file}.bak"
    done
  fi
done

log "Generating $STATIC_API_YAML"
: > "$STATIC_API_YAML"
# Only include major version directories in the static API listing
for major_version in $(printf '%s\n' "${!major_versions_map[@]}" | sort -V); do
  if [[ -d "$STATIC_DIR/$major_version" ]]; then
    find "$STATIC_DIR/$major_version" -type f -name '*.html' | sort | while read -r file; do
      echo "- url: ${file#$STATIC_DIR/}" >> "$STATIC_API_YAML"
    done
  fi
done

log "Adding pagefind attributes to API documentation HTML files"
for major_version in $(printf '%s\n' "${!major_versions_map[@]}" | sort -V); do
  if [[ -d "$STATIC_DIR/$major_version" ]]; then
    log "Processing $major_version HTML files for pagefind"
    "$SCRIPT_DIR/add_pagefind_attributes.sh" "$STATIC_DIR/$major_version" "api" "TrueNAS API"
  fi
done

log "TrueNAS API docs have been updated in $STATIC_DIR"