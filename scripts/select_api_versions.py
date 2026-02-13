#!/usr/bin/env python3
"""
Intelligent API version selection based on TrueNAS release data.

Prioritizes versions marked as latest=true in scale-releases.yaml over
higher semantic versions that are unreleased development builds.

Usage:
    python3 select_api_versions.py <scale-releases.yaml> <version1> <version2> ...

Output:
    JSON mapping of major version -> selected minor version
    Example: {"v24.10": "v24.10", "v25.04": "v25.04.1", "v25.10": "v25.10.2"}
"""

import sys
import json
import re
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
        v26.04.0 -> "26.04"

    Returns major version without 'v' prefix.
    """
    # Remove 'v' prefix if present
    version = version_string.lstrip('v')

    # Split by dots and take first two parts (Year.Month)
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

    # Sort by semantic version
    sorted_matches = sorted(matches, key=lambda v: [int(x) if x.isdigit() else x for x in v.lstrip('v').split('.')], reverse=True)

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


def select_versions(release_data: Dict, available_versions: List[str]) -> Dict[str, str]:
    """
    Select one version per major version based on release data.

    Priority:
    1. Versions with latest=true in scale-releases.yaml
    2. Among latest versions, prioritize: Maintenance > Early > Experimental
    3. Fallback to highest semver for majors not in release data

    Returns dict mapping major version -> selected directory name
    """
    selected = {}
    matched_majors = set()

    # Priority order for release types
    type_priority = {
        'Maintenance': 3,
        'Early': 2,
        'Experimental': 1,
    }

    # Process each major version in release data
    for major_version_group in release_data.get('majorVersions', []):
        latest_releases = []

        # Find all releases with latest=true
        for release in major_version_group.get('releases', []):
            if release.get('latest'):
                release_name = release.get('name', '')
                release_type = release.get('type', 'Experimental')

                parsed = parse_release_version(release_name)
                if parsed:
                    major, full_version = parsed

                    # Find matching directory
                    matched_dir = match_release_to_directory(full_version, available_versions)
                    if matched_dir:
                        priority = type_priority.get(release_type, 0)
                        latest_releases.append((major, matched_dir, priority, release_type))
                        matched_majors.add(major)

        # Select the highest priority latest release for this major version
        if latest_releases:
            # Sort by priority (highest first)
            latest_releases.sort(key=lambda x: x[2], reverse=True)
            major, selected_dir, _, release_type = latest_releases[0]

            # Use major version as key (with v prefix)
            selected[f"v{major}"] = selected_dir

    # Handle versions not in release data (fallback to semver)
    available_by_major = {}
    for version in available_versions:
        major = extract_major_version(version)
        if major not in matched_majors:
            if major not in available_by_major:
                available_by_major[major] = []
            available_by_major[major].append(version)

    # For each unmatched major, select highest semver
    for major, versions in available_by_major.items():
        sorted_versions = sorted(versions, key=lambda v: [int(x) if x.isdigit() else x for x in v.lstrip('v').split('.')], reverse=True)
        selected[f"v{major}"] = sorted_versions[0]

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
