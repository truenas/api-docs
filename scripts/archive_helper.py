#!/usr/bin/env python3
"""
Read scale-releases.yaml and emit archive-related artifacts.

Subcommands:
    list     Print lifecycle of each archived major, one per line.
    exclude  Write an rclone --exclude-from file covering archived paths.
    resolve  Write the effective archive list (api_archived.yaml).

Majors are archived explicitly via the `state: "archived"` field on entries
in `majorVersions:` in `scale-releases.yaml`, or automatically: a `previous`
major that is published on storj but was not produced by this build (the
middleware image stopped shipping it) is treated as archived so that
`rclone sync` does not delete it and it surfaces on /archive/.
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


def dir_major(lifecycle):
    """Directory-major form of a lifecycle: integer lifecycles ("27") map to "27.0"."""
    return lifecycle if "." in lifecycle else f"{lifecycle}.0"


def resolve_archived(data, built, published):
    """Return the effective archived entries as a list of dicts.

    built:     set of major directory names produced by this build (e.g. "v25.10").
    published: set of top-level directory names already on storj, or None when
               the listing is unavailable (auto-archive is then skipped).

    Explicit `state: "archived"` entries always come first. A `previous` major
    is auto-archived only when it is absent from `built` and present in
    `published`; other states are never auto-archived.
    """
    out = []
    for mv in data.get("majorVersions", []):
        lifecycle = mv["lifecycle"]
        entry = {
            "lifecycle": lifecycle,
            "path": lifecycle,
            "name": mv.get("name", ""),
            "releaseName": mv.get("releaseName", ""),
        }
        if mv.get("state") == "archived":
            entry["auto"] = False
            out.append(entry)
        elif mv.get("state") == "previous" and published is not None:
            candidates = [f"v{lifecycle}", f"v{dir_major(lifecycle)}"]
            if any(c in built for c in candidates):
                continue
            found = next((c for c in candidates if c in published), None)
            if found:
                entry["path"] = found[1:]
                entry["auto"] = True
                out.append(entry)
    return out


def load_archived_file(path):
    """Return (lifecycle, path) pairs from a file written by `resolve`."""
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return [(a["lifecycle"], a["path"]) for a in data.get("archived", [])]


def _archived_pairs(args):
    if getattr(args, "archived_file", None):
        return load_archived_file(args.archived_file)
    return [(lc, lc) for lc in archived_majors(args.yaml)]


def _read_names(path):
    if not path:
        return None
    with open(path) as f:
        return {line.strip().strip("/") for line in f if line.strip()}


def cmd_list(args):
    for lifecycle, _ in _archived_pairs(args):
        print(lifecycle)
    return 0


def cmd_resolve(args):
    with open(args.yaml) as f:
        data = yaml.safe_load(f) or {}
    built = _read_names(args.built) or set()
    published = _read_names(args.published)
    entries = resolve_archived(data, built, published)
    for mv in data.get("majorVersions", []):
        lc = mv["lifecycle"]
        if mv.get("state") in ("ga", "early", "preview") and not (
            {f"v{lc}", f"v{dir_major(lc)}"} & built
        ):
            msg = f"{mv['state']} major {lc} has no built docs directory"
            if mv["state"] == "ga":
                print(f"ERROR: {msg}; refusing to publish without the current release", file=sys.stderr)
                return 3
            print(f"WARNING: {msg}", file=sys.stderr)
    with open(args.output, "w") as out:
        yaml.safe_dump({"archived": entries}, out, sort_keys=False)
    for e in entries:
        if e["auto"]:
            print(f"Auto-archived {e['lifecycle']} (published on storj, not built)", file=sys.stderr)
    return 0


def cmd_exclude(args):
    """
    Write rclone --exclude-from patterns for each archived major.

    Two patterns per major:
      v{lifecycle}/**       — protects the canonical major-version directory.
      v{lifecycle}.*/**     — protects minor-version redirect directories.
    """
    with open(args.output, "w") as out:
        for _, path in _archived_pairs(args):
            out.write(f"v{path}/**\n")
            out.write(f"v{path}.*/**\n")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml", help="Path to scale-releases.yaml")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="Print archived lifecycles, one per line")
    p_list.add_argument("--archived-file", help="Use a file written by `resolve`")
    p_list.set_defaults(func=cmd_list)

    p_res = sub.add_parser("resolve", help="Write effective archive list (yaml)")
    p_res.add_argument("--built", help="File listing major dirs built, one per line")
    p_res.add_argument("--published", help="File listing top-level dirs on storj (omit to skip auto-archive)")
    p_res.add_argument("--output", required=True, help="Output yaml path")
    p_res.set_defaults(func=cmd_resolve)

    p_excl = sub.add_parser("exclude", help="Write rclone exclude-from file")
    p_excl.add_argument("--archived-file", help="Use a file written by `resolve`")
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
