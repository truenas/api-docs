"""Tests for archive_helper.py."""
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).parent / "archive_helper.py"


def write_yaml(tmp_path, majorVersions):
    """Helper to write a scale-releases.yaml with given majorVersions."""
    p = tmp_path / "scale-releases.yaml"
    p.write_text(yaml.safe_dump({"majorVersions": majorVersions}))
    return str(p)


def run(*args):
    """Run archive_helper.py and return (stdout, stderr, returncode)."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True
    )
    return result.stdout, result.stderr, result.returncode


def test_list_no_archived(tmp_path):
    yaml_path = write_yaml(tmp_path, [
        {"lifecycle": "25.10", "state": "ga"},
        {"lifecycle": "26", "state": "early"},
    ])
    out, _, rc = run(yaml_path, "list")
    assert rc == 0
    assert out.strip() == ""


def test_list_one_archived(tmp_path):
    yaml_path = write_yaml(tmp_path, [
        {"lifecycle": "22.12", "state": "archived"},
        {"lifecycle": "25.10", "state": "ga"},
    ])
    out, _, rc = run(yaml_path, "list")
    assert rc == 0
    assert out.strip() == "22.12"


def test_list_multiple_archived(tmp_path):
    yaml_path = write_yaml(tmp_path, [
        {"lifecycle": "22.12", "state": "archived"},
        {"lifecycle": "24.04", "state": "archived"},
        {"lifecycle": "25.10", "state": "ga"},
    ])
    out, _, rc = run(yaml_path, "list")
    assert rc == 0
    assert out.strip().splitlines() == ["22.12", "24.04"]


def test_exclude_writes_two_patterns_per_archived(tmp_path):
    yaml_path = write_yaml(tmp_path, [
        {"lifecycle": "22.12", "state": "archived"},
        {"lifecycle": "24.04", "state": "archived"},
        {"lifecycle": "25.10", "state": "ga"},
    ])
    output_path = tmp_path / "exclude.txt"
    _, _, rc = run(yaml_path, "exclude", "--output", str(output_path))
    assert rc == 0
    contents = output_path.read_text().splitlines()
    assert contents == [
        "v22.12/**",
        "v22.12.*/**",
        "v24.04/**",
        "v24.04.*/**",
    ]


def test_exclude_empty_when_no_archived(tmp_path):
    yaml_path = write_yaml(tmp_path, [
        {"lifecycle": "25.10", "state": "ga"},
    ])
    output_path = tmp_path / "exclude.txt"
    _, _, rc = run(yaml_path, "exclude", "--output", str(output_path))
    assert rc == 0
    assert output_path.read_text() == ""


def test_missing_state_treated_as_not_archived(tmp_path):
    """Tolerate older YAML entries that haven't gained a state field yet."""
    yaml_path = write_yaml(tmp_path, [
        {"lifecycle": "20.10"},
        {"lifecycle": "25.10", "state": "ga"},
    ])
    out, _, rc = run(yaml_path, "list")
    assert rc == 0
    assert out.strip() == ""


def test_missing_yaml_file_exits_nonzero(tmp_path):
    bogus = tmp_path / "nonexistent.yaml"
    _, _, rc = run(str(bogus), "list")
    assert rc != 0
