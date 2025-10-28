# api-docs
API Documentation Website

This is an almost entirely automated website to generate and serve TrueNAS API documentation.

To build locally, Docker and Hugo v0.145 (or newer) is required. Git for Windows is also helpful, or Git bash generally for running the scripts.
Make sure Docker is running.

1. Execute **scripts/pull_api_docs.sh** and wait for it to complete (it can take some time).
2. Execute **scripts/remove_current_labeling.sh**
3. Execute **scripts/pull-truenas-release-data**
4. In a terminal, run `hugo serve`.
5. (Optional) Run `npx pagefind --site public` to build the search index.

To cleanup, execute **scripts/cleanup_api_docs.sh**.

The scripts/pull_api_docs.sh script creates a docker container from an upstream TrueNAS container, places the Sphinx-rendered API documentation files into the static/ directory, and generates some data/ files that are used by Hugo at buildtime.

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
