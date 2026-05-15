#!/usr/bin/env python3
"""
Read scale-releases.yaml and emit archive-related artifacts.

Subcommands:
    list     Print lifecycle of each archived major, one per line.
    exclude  Write an rclone --exclude-from file covering archived paths.

The single source of truth for which majors are archived is the
`state: "archived"` field on entries in `majorVersions:` in
`scale-releases.yaml`.
"""
import argparse
import sys

import yaml


def archived_majors(yaml_path):
    """Return list of `lifecycle` values for majors with state == 'archived'."""
    with open(yaml_path) as f:
        data = yaml.safe_load(f) or {}
    return [
        mv["lifecycle"]
        for mv in data.get("majorVersions", [])
        if mv.get("state") == "archived"
    ]


def cmd_list(args):
    for lifecycle in archived_majors(args.yaml):
        print(lifecycle)
    return 0


def cmd_exclude(args):
    """
    Write rclone --exclude-from patterns for each archived major.

    Two patterns per major:
      v{lifecycle}/**       — protects the canonical major-version directory.
      v{lifecycle}.*/**     — protects minor-version redirect directories.
    """
    with open(args.output, "w") as out:
        for lifecycle in archived_majors(args.yaml):
            out.write(f"v{lifecycle}/**\n")
            out.write(f"v{lifecycle}.*/**\n")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml", help="Path to scale-releases.yaml")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="Print archived lifecycles, one per line")
    p_list.set_defaults(func=cmd_list)

    p_excl = sub.add_parser("exclude", help="Write rclone exclude-from file")
    p_excl.add_argument("--output", required=True, help="Output file path")
    p_excl.set_defaults(func=cmd_exclude)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
