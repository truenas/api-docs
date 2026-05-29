#!/usr/bin/env python3
"""
Intelligent API version selection based on TrueNAS release data.

Selects, per major version, the entry with the most recent shipped
`releaseDate` (parseable date <= today) from scale-releases.yaml. This
prevents the script from publishing API docs for unreleased development
builds whose directories happen to outrank the actual shipped release in
semver order.

Usage:
    python3 select_api_versions.py <scale-releases.yaml> <version1> <version2> ...

Output:
    JSON mapping of major version -> selected minor version
    Example: {"v24.10": "v24.10", "v25.04": "v25.04.1", "v25.10": "v25.10.2"}
"""

import sys
import json
import re
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def log_error(msg: str) -> None:
    """Print error message to stderr."""
    print(f"ERROR: {msg}", file=sys.stderr)


def extract_major_version(version_string: str) -> str:
    """
    Extract major version from API version string.

    Examples:
        v24.10 -> "24.10"
        v24.10.2.4 -> "24.10"
        v25.04.0 -> "25.04"
        v25.10.2 -> "25.10"
        v25.10-BETA.1 -> "25.10"
        v26.0.0 -> "26.0"
        v26.0.0-BETA.1 -> "26.0"
        v26.1.0 -> "26.1"

    Returns major version without 'v' prefix.
    """
    # Remove 'v' prefix if present
    version = version_string.lstrip('v')

    # Strip hyphenated pre-release suffix (BETA.1, RC.1) before splitting, so
    # pre-release directories don't get bucketed under a bogus "X.Y-BETA" major.
    if '-' in version:
        version = version.split('-', 1)[0]

    # Split by dots and take first two parts (Year.Month or semver Major.Minor)
    parts = version.split('.')
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}"

    # Fallback: return as-is (shouldn't happen with valid versions)
    return version


def parse_release_version(release_name: str) -> Optional[Tuple[str, str]]:
    """
    Parse version from release name in scale-releases.yaml.

    Examples:
        "24.10.2.2" -> ("24.10", "24.10.2.2")
        "25.04.1" -> ("25.04", "25.04.1")
        "25.10 Nightlies" -> ("25.10", "25.10")
        "25.10-BETA.1" -> ("25.10", "25.10-BETA.1")

    Returns (major_version, full_version) or None if unable to parse.
    """
    # Extract version numbers from the name (handle descriptive names like "25.10 Nightlies")
    match = re.match(r'^(\d+)\.(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([A-Z]+\.\d+))?', release_name)
    if match:
        year, month, patch, subpatch, prerelease = match.groups()
        major = f"{year}.{month}"

        # Reconstruct full version
        full_parts = [year, month]
        if patch:
            full_parts.append(patch)
        if subpatch:
            full_parts.append(subpatch)
        full_version = '.'.join(full_parts)
        if prerelease:
            full_version += f"-{prerelease}"

        return (major, full_version)

    # Handle special cases like "25.10 Nightlies"
    match = re.match(r'^(\d+)\.(\d+)\s+\w+', release_name)
    if match:
        year, month = match.groups()
        major = f"{year}.{month}"
        return (major, major)  # Use major as full version for nightlies

    return None


def match_release_to_directory(release_version: str, available_versions: List[str]) -> Optional[str]:
    """
    Find the directory that matches a release version.

    Examples:
        "24.10.2.2" matches "v24.10" (exact major match is good enough)
        "25.04.1" matches "v25.04.1" (exact match preferred)
        "25.10" matches highest of "v25.10.0", "v25.10.1", "v25.10.2" (for Nightlies)

    Returns directory name (with 'v' prefix) or None.
    """
    major = extract_major_version(release_version)
    matches = [v for v in available_versions if extract_major_version(v) == major]

    if not matches:
        return None

    # Sort highest-first using the pre-release-aware comparator (see _sort_versions_desc).
    sorted_matches = _sort_versions_desc(matches)

    # For exact patch-level matches, prefer the exact version
    exact_match = f"v{release_version}"
    if exact_match in sorted_matches:
        # If it's not a major-only version (has patch numbers), prefer exact match
        if release_version.count('.') >= 2:
            return exact_match

    # Otherwise (or for major-only versions like "25.10" from Nightlies), return highest
    return sorted_matches[0]


def load_release_data(yaml_path: str) -> Optional[Dict]:
    """Load and parse scale-releases.yaml file."""
    try:
        import yaml
    except ImportError:
        log_error("PyYAML not installed. Install with: pip install pyyaml")
        return None

    try:
        with open(yaml_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        log_error(f"Release data file not found: {yaml_path}")
        return None
    except yaml.YAMLError as e:
        log_error(f"Failed to parse YAML: {e}")
        return None
    except Exception as e:
        log_error(f"Unexpected error loading release data: {e}")
        return None


def _parse_release_date(rd):
    """Return a datetime.date for ISO yyyy-mm-dd strings, else None.

    Sentinel strings used in scale-releases.yaml ("TBD" for unscheduled future
    releases, "Ongoing" for continuous nightly tracks) and empty/missing dates
    all return None — they do not represent a shipped point-in-time release.
    """
    if not rd or rd in ('TBD', 'Ongoing'):
        return None
    try:
        return datetime.date.fromisoformat(rd)
    except (ValueError, TypeError):
        return None


def _sort_versions_desc(versions: List[str]) -> List[str]:
    """Sort version directory names highest-first, tolerating pre-release suffixes.

    Each dotted component is split into (leading-int, is-stable, trailing-str)
    so mixed parts compare cleanly without TypeErrors AND pre-release suffixes
    sort *below* the corresponding stable version (semver convention):
        v25.10.3.1     -> [(25,True,""), (10,True,""), (3,True,""), (1,True,"")]
        v25.10-BETA.1  -> [(25,True,""), (10,False,"-BETA"), (1,True,"")]
    25.10.3.1 sorts higher than 25.10-BETA.1 because (10,True,"") > (10,False,"-BETA").
    """
    def key(v):
        out = []
        for part in v.lstrip('v').split('.'):
            m = re.match(r'(\d+)(.*)$', part)
            if m:
                n = int(m.group(1))
                suffix = m.group(2)
                # `suffix == ''` is True for stable, False for pre-release; True
                # sorts greater than False, so stable beats pre-release.
                out.append((n, suffix == '', suffix))
            else:
                out.append((0, False, part))
        return out
    return sorted(versions, key=key, reverse=True)


def _dir_major_for_lifecycle(lifecycle: str) -> str:
    """Map a yaml lifecycle to the directory-major form `extract_major_version` returns.

    YY.MM lifecycles (e.g., "25.10") match their own form. Integer lifecycles
    (e.g., "26") map to `<lifecycle>.0` — the API directories use semver (26.0.0,
    26.1.0, 26.0.1), so `extract_major_version("v26.0.0")` returns "26.0".
    This mirrors the existing archived-majors bridge.
    """
    return lifecycle if '.' in lifecycle else f"{lifecycle}.0"


def select_versions(release_data: Dict, available_versions: List[str]) -> Dict[str, str]:
    """
    Select one version per major version based on release data.

    Strategy:
    1. For each non-archived major, pick the release entry with the most recent
       `releaseDate` that's a parseable date <= today (i.e., the latest shipped
       release). Type priority breaks ties when multiple entries share a date
       (rare): Maintenance/Stable > Early Release > Experimental.
    2. If a major has no dated/shipped entries (e.g., nightlies-only majors in
       the `preview` state where every entry has `releaseDate: "Ongoing"`), fall
       back to the highest-priority "Ongoing" entry so the major is still
       represented in the API docs.
    3. For majors not present in release data at all, fall back to the highest
       semver directory in `available_versions`.

    Majors marked `state: "archived"` are excluded entirely — they do not
    appear in the returned mapping and therefore not in api_versions.yaml.
    The api-docs site renders archived versions separately (via the
    api_archived shortcode), and the live docs are served from storj
    independently of this build.

    Returns dict mapping major version -> selected directory name
    """
    # Identify archived majors so we can skip them in both the
    # release-data loop and the unmatched-fallback loop below.
    # Includes each lifecycle plus a `<year>.0` form for the TrueNAS 26+
    # naming format — e.g., YAML `lifecycle: "26"` matches both the
    # canonical "26" and what extract_major_version() returns for v26.0.0
    # ("26.0"). This is defense-in-depth: the bash pull script also
    # removes archived directories before this script runs.
    archived_majors = set()
    for mv in release_data.get('majorVersions', []):
        if mv.get('state') == 'archived':
            lifecycle = mv['lifecycle']
            archived_majors.add(lifecycle)
            if '.' not in lifecycle:
                archived_majors.add(f"{lifecycle}.0")

    selected = {}
    matched_majors = set()
    today = datetime.date.today()

    # Priority order for release types — matches the `type:` strings used in
    # scale-releases.yaml. Used as a tiebreaker when entries share a date, and
    # for picking among multiple "Ongoing" entries in the nightlies fallback.
    type_priority = {
        'Maintenance': 3,
        'Stable': 3,
        'Early Release': 2,
        'Experimental': 1,
    }

    # Process each major version in release data
    for major_version_group in release_data.get('majorVersions', []):
        if major_version_group.get('state') == 'archived':
            continue

        releases = major_version_group.get('releases', [])

        # Collect every release whose date parses and is on/before today.
        shipped = []
        for release in releases:
            d = _parse_release_date(release.get('releaseDate'))
            if d is not None and d <= today:
                priority = type_priority.get(release.get('type', ''), 0)
                shipped.append((d, priority, release))

        candidate = None
        if shipped:
            # Most recent date wins; type priority breaks ties.
            shipped.sort(key=lambda x: (x[0], x[1]), reverse=True)
            candidate = shipped[0][2]
        else:
            # No dated/shipped entries — try the nightlies fallback.
            ongoing = [r for r in releases if r.get('releaseDate') == 'Ongoing']
            if ongoing:
                ongoing.sort(
                    key=lambda r: type_priority.get(r.get('type', ''), 0),
                    reverse=True,
                )
                candidate = ongoing[0]

        if not candidate:
            continue

        lifecycle = major_version_group.get('lifecycle', '')
        if not lifecycle:
            continue
        dir_major = _dir_major_for_lifecycle(lifecycle)

        # First try an exact release-name → directory match (works for
        # YY.MM patches like 25.10.3.1 where the yaml release name and the
        # directory name align).
        matched_dir = None
        parsed = parse_release_version(candidate.get('name', ''))
        if parsed:
            _, full_version = parsed
            matched_dir = match_release_to_directory(full_version, available_versions)

        # No exact match — bridge from yaml lifecycle to directory major and
        # pick the highest semver among directories belonging to this lifecycle.
        # Covers integer-lifecycle cases (yaml "26-BETA.1" doesn't match
        # directory "v26.0.0-BETA.1" literally, but both belong to dir_major "26.0").
        if not matched_dir:
            bridged = [v for v in available_versions if extract_major_version(v) == dir_major]
            if bridged:
                matched_dir = _sort_versions_desc(bridged)[0]

        if matched_dir:
            selected[f"v{dir_major}"] = matched_dir
            matched_majors.add(dir_major)
            if '.' not in lifecycle:
                # Mirror the archived-majors bridge so the fallback loop below
                # doesn't re-emit the lifecycle under its branding-only key.
                matched_majors.add(lifecycle)

    # Handle versions not in release data (fallback to semver)
    available_by_major = {}
    for version in available_versions:
        major = extract_major_version(version)
        if major in archived_majors:
            continue
        if major not in matched_majors:
            if major not in available_by_major:
                available_by_major[major] = []
            available_by_major[major].append(version)

    # For each unmatched major, select highest semver
    for major, versions in available_by_major.items():
        selected[f"v{major}"] = _sort_versions_desc(versions)[0]

    return selected


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: select_api_versions.py <scale-releases.yaml> <version1> <version2> ...", file=sys.stderr)
        sys.exit(1)

    yaml_path = sys.argv[1]
    available_versions = sys.argv[2:]

    # Load release data
    release_data = load_release_data(yaml_path)
    if not release_data:
        # Failed to load, exit with error so bash can fall back
        sys.exit(1)

    # Select versions
    try:
        selected = select_versions(release_data, available_versions)

        # Output as JSON
        print(json.dumps(selected, sort_keys=True))
        sys.exit(0)

    except Exception as e:
        log_error(f"Failed to select versions: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
