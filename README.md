# api-docs
API Documentation Website

This is an almost entirely automated website to generate and serve TrueNAS API documentation.

To build locally, Docker and Hugo v0.145 (or newer) is required. Git for Windows is also helpful, or Git bash generally for running the scripts.
Make sure Docker is running.

1. Execute **scripts/pull_api_docs.sh** and wait for it to complete (it can take some time).
2. Execute **scripts/remove_current_labeling.sh**
3. In a terminal, run `hugo serve`.

To cleanup, execute **scripts/cleanup_api_docs.sh**.

The scripts/pull_api_docs.sh script creates a docker container from an upstream TrueNAS container, places the Sphinx-rendered API documentation files into the static/ directory, and generates some data/ files that are used by Hugo at buildtime.
