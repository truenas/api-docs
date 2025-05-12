# api-docs
API Documentation Website

This is an almost entirely automated website to generate and serve TrueNAS API documentation.

To build locally, Docker and Hugo v0.145 (or newer) is required.

The scripts/pull_api_docs.sh script creates a docker container from an upstream TrueNAS container, places the Sphinx-rendered API documentation files into the static/ directory, and generates some data/ files that are used by Hugo at buildtime.
