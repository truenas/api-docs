#!/bin/bash

# Build script for TrueNAS API Documentation
# This script fetches external data and builds the Hugo site

set -e  # Exit on any error

echo "🚀 Building TrueNAS API Documentation..."

# Step 1: Fetch external data
echo "📡 Fetching external data..."
./scripts/fetch-data.sh

# Step 2: Build the Hugo site
echo "🔨 Building Hugo site..."
hugo -d public --gc --minify --cleanDestinationDir

echo "✅ Build complete! Site generated in ./public/"