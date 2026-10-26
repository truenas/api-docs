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


def write_names(tmp_path, name, names):
    p = tmp_path / name
    p.write_text("".join(f"{n}\n" for n in names))
    return str(p)


def resolve(tmp_path, majors, built, published):
    yaml_path = write_yaml(tmp_path, majors)
    out_path = tmp_path / "api_archived.yaml"
    args = [yaml_path, "resolve", "--output", str(out_path),
            "--built", write_names(tmp_path, "built.txt", built)]
    if published is not None:
        args += ["--published", write_names(tmp_path, "published.txt", published)]
    _, _, rc = run(*args)
    assert rc == 0
    return yaml.safe_load(out_path.read_text())["archived"]


MAJORS = [
    {"lifecycle": "24.10", "state": "archived", "name": "TrueNAS 24.10"},
    {"lifecycle": "25.04", "state": "previous", "name": "TrueNAS 25.04", "releaseName": "Fangtooth"},
    {"lifecycle": "25.10", "state": "ga"},
    {"lifecycle": "27", "state": "early"},
]


def test_resolve_auto_archives_dropped_previous(tmp_path):
    got = resolve(tmp_path, MAJORS, ["v25.10", "v27.0"],
                  ["v24.10", "v25.04", "v25.10", "v27.0"])
    assert [(a["lifecycle"], a["auto"]) for a in got] == [("24.10", False), ("25.04", True)]
    assert got[1]["path"] == "v25.04"[1:]
    assert got[1]["releaseName"] == "Fangtooth"


def test_resolve_keeps_previous_when_built(tmp_path):
    got = resolve(tmp_path, MAJORS, ["v25.04", "v25.10", "v27.0"], ["v25.04", "v25.10"])
    assert [a["lifecycle"] for a in got] == ["24.10"]


def test_resolve_skips_previous_never_published(tmp_path):
    got = resolve(tmp_path, MAJORS, ["v25.10"], ["v24.10", "v25.10"])
    assert [a["lifecycle"] for a in got] == ["24.10"]


def test_resolve_without_listing_skips_auto_archive(tmp_path):
    got = resolve(tmp_path, MAJORS, ["v25.10"], None)
    assert [a["lifecycle"] for a in got] == ["24.10"]


def test_resolve_never_auto_archives_other_states(tmp_path):
    got = resolve(tmp_path, MAJORS, ["v25.10"], ["v25.10", "v27.0", "v27"])
    assert [a["lifecycle"] for a in got] == ["24.10"]


def test_resolve_integer_lifecycle_uses_published_dir_name(tmp_path):
    majors = [{"lifecycle": "27", "state": "previous"}, {"lifecycle": "28", "state": "ga"}]
    got = resolve(tmp_path, majors, ["v28.0"], ["v27.0", "v28.0"])
    assert got[0]["path"] == "27.0"


def test_exclude_and_list_use_resolved_file(tmp_path):
    yaml_path = write_yaml(tmp_path, MAJORS)
    resolved = tmp_path / "api_archived.yaml"
    run(yaml_path, "resolve", "--output", str(resolved),
        "--built", write_names(tmp_path, "b.txt", ["v25.10", "v27.0"]),
        "--published", write_names(tmp_path, "p.txt", ["v24.10", "v25.04"]))
    out, _, rc = run(yaml_path, "list", "--archived-file", str(resolved))
    assert rc == 0 and out.split() == ["24.10", "25.04"]
    excl = tmp_path / "exclude.txt"
    run(yaml_path, "exclude", "--archived-file", str(resolved), "--output", str(excl))
    assert excl.read_text().splitlines() == [
        "v24.10/**", "v24.10.*/**", "v25.04/**", "v25.04.*/**",
    ]


def test_resolve_fails_when_ga_not_built(tmp_path):
    yaml_path = write_yaml(tmp_path, MAJORS)
    _, err, rc = run(yaml_path, "resolve", "--output", str(tmp_path / "o.yaml"),
                     "--built", write_names(tmp_path, "b.txt", ["v27.0"]))
    assert rc == 3
    assert "25.10" in err


def test_resolve_warns_only_when_early_not_built(tmp_path):
    yaml_path = write_yaml(tmp_path, MAJORS)
    _, err, rc = run(yaml_path, "resolve", "--output", str(tmp_path / "o.yaml"),
                     "--built", write_names(tmp_path, "b.txt", ["v25.10"]))
    assert rc == 0
    assert "WARNING" in err
