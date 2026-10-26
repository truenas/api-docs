# api-docs

API Documentation Website

This is an almost entirely automated website to generate and serve TrueNAS API documentation.

To build locally, Docker and Hugo Extended v0.157.0 is required. Git for Windows is also helpful, or Git bash generally for running the scripts.
Make sure Docker is running.

**Install Hugo Extended (Windows — Chocolatey, run PowerShell as Administrator):**

    choco install hugo-extended --version=0.157.0

**Windows (winget):**

    winget install Hugo.Hugo.Extended --version 0.157.0

**WSL/Linux:** Download `hugo_extended_0.157.0_linux-amd64.tar.gz` from
https://github.com/gohugoio/hugo/releases/tag/v0.157.0 and install to your PATH.

> Hugo Extended (not standard Hugo) is required. This site has been tested against v0.157.0.
> Later versions may work but have not been officially tested.

1. Execute **scripts/pull-truenas-release-data.sh** (fetches `scale-releases.yaml`; required before the next step).
2. Execute **scripts/pull_api_docs.sh** and wait for it to complete (it can take some time — the first run downloads the multi-GB `ghcr.io/truenas/middleware:master` image).
3. Execute **scripts/remove_current_labeling.sh**
4. In a terminal, run `hugo serve`.
5. (Optional) Run `npx pagefind --site public` to build the search index.

To cleanup, execute **scripts/cleanup_api_docs.sh**.

The scripts/pull_api_docs.sh script creates a docker container from an upstream TrueNAS container, places the Sphinx-rendered API documentation files into the static/ directory, and generates some data/ files that are used by Hugo at buildtime.

## Archived Versions

Older versions are moved off the homepage and listed at `/archive/`. A version is archived in one of two ways:

- **Explicitly:** set `state: "archived"` for the major in `scale-releases.yaml`.
- **Automatically:** a `previous` major that is already published to the bucket but is no longer produced by the build (the middleware image stopped shipping its docs) is treated as archived.

During `scripts/pull_api_docs.sh`, `scripts/archive_helper.py resolve` combines both into `data/api_archived.yaml` (generated, not committed). That file drives the `/archive/` page and the rclone exclude list, so archived versions are never deleted by `rclone sync`. Auto-archive only applies to `previous` versions that are already published, and is skipped if the bucket listing is unavailable. The build fails if the current GA major has no built docs.

Archived docs are not rebuilt. `archive-backups/vX.Y/` holds a snapshot of each one, and the Jenkins job runs `rclone copy archive-backups ...` before each build to restore any that are missing from the bucket (`copy` never deletes).

To snapshot a version that is about to be archived, copy its built output into the repo and commit it:

    cp -r public/vX.Y archive-backups/vX.Y

Tests: `python3 -m pytest scripts/test_archive_helper.py`.

## Pagefind Search Integration

This repository integrates with [Pagefind](https://pagefind.app/) for multi-site static keyword search across TrueNAS documentation.

### How It Works

1. **Post-Processing Script**: `scripts/add_pagefind_attributes.sh` adds necessary `data-pagefind-*` attributes to Sphinx-generated HTML files for proper indexing
2. **Automatic Integration**: The `pull_api_docs.sh` script automatically runs the post-processing script after pulling API docs
3. **Index Generation**: Run `npx pagefind --site public` to generate the search index
4. **Configuration**: `pagefind.yml` contains exclusion rules for navigation and non-content elements

### Scripts

- **scripts/add_pagefind_attributes.sh** - Pure bash script to add pagefind attributes to HTML files
- **scripts/process_existing_docs.sh** - Process already-built API docs in the `public/` directory

### Usage

To manually process existing API documentation for pagefind:

```bash
# Process all version directories in public/
./scripts/process_existing_docs.sh

# Or process a specific version
./scripts/add_pagefind_attributes.sh public/v25.04 api "TrueNAS API"

# Rebuild the search index
npx pagefind --site public
```

### Multi-Site Search

This site is configured for multi-site search with:
- **Site Key**: `api`
- **Site Name**: `TrueNAS API`

These identifiers allow the main documentation site to filter and display API documentation results alongside other TrueNAS sites.
