#!/bin/bash

# Fetch external data script for TrueNAS API Documentation
# This script downloads the scale-releases.yaml file from the TrueNAS documentation repository

echo "Fetching scale-releases.yaml from TrueNAS documentation repository..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Go up one level to the api-docs root directory
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create the data/properties directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/data/properties"

# Fetch the scale-releases.yaml file
curl -L -o "$PROJECT_ROOT/data/properties/scale-releases.yaml" \
  "https://raw.githubusercontent.com/truenas/documentation/master/data/properties/scale-releases.yaml"

if [ $? -eq 0 ]; then
    echo "✅ Successfully fetched scale-releases.yaml"
else
    echo "❌ Failed to fetch scale-releases.yaml"
    exit 1
fi

echo "Data fetch complete!"