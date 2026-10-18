# ============================================================
# test_change_index.py
# Tests for change_index.py, the index RIDGE uses to tell what
# changed since the last post (ADR-0008).
#
# Every test here was written before the code it checks, so each
# one is marked as an expected failure. When a function gets built
# and its tests start passing, pytest reports them as FAILED with
# XPASS(strict). That's the reminder to delete the marker line
# above each of them.
#
# The scan tests read config.example.yml and the demo project, the
# same way test_records.py does. The hash tests only need two small
# files with known text, so they write them into tmp_path.
# ============================================================
from pathlib import Path

import pytest

from change_index import hash_file_text, scan_project
from config import MARKER_FILE_NAME, load_config, read_marker, resolve_project_location
from records import resolve_included_patterns

EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.example.yml"


def scan_example_project():
    # Scan the first project in the example config, the same way the
    # real run will.
    config_data = load_config(EXAMPLE_CONFIG_PATH)
    project_location = resolve_project_location(
        EXAMPLE_CONFIG_PATH, config_data["projects"][0]["project_path"]
    )
    marker_file = read_marker(project_location / MARKER_FILE_NAME)
    conventions = marker_file.get("conventions", {})
    included_patterns = resolve_included_patterns(marker_file, project_location)
    return scan_project(project_location, conventions, included_patterns)


# ---------- hash_file_text ----------


# The same words saved with Windows line endings and with Linux
# line endings should give the same fingerprint. Otherwise RIDGE
# would report a change every time git or an editor switched them.
def test_hash_ignores_line_endings(tmp_path):
    windows_file = tmp_path / "windows.md"
    linux_file = tmp_path / "linux.md"
    windows_file.write_bytes(b"first line\r\nsecond line\r\n")
    linux_file.write_bytes(b"first line\nsecond line\n")

    assert hash_file_text(windows_file) == hash_file_text(linux_file)


# Changing one word has to change the fingerprint.
def test_hash_changes_when_text_changes(tmp_path):
    original = tmp_path / "original.md"
    edited = tmp_path / "edited.md"
    original.write_text("M3 is planned\n", encoding="utf-8")
    edited.write_text("M3 is in progress\n", encoding="utf-8")

    assert hash_file_text(original) != hash_file_text(edited)


# ---------- scan_project ----------


# Every allowed file in the demo gets an entry, keyed by its path
# relative to the project folder, written with forward slashes.
def test_scan_finds_every_allowed_file():
    index = scan_example_project()

    assert "docs/sessions/2026-09-21-demo-001-valid-sample.md" in index
    assert "docs/decisions/0001-sample-decision.md" in index
    assert "docs/milestones/P1-M1-sample-milestone.md" in index


# The .txt sample isn't allowed by the demo's included_patterns,
# so it never gets an entry.
def test_scan_skips_files_not_in_included_patterns():
    index = scan_example_project()

    assert "docs/sessions/2026-09-21-demo-006-not-markdown.txt" not in index


# The scan lists files. It doesn't judge them, so the broken samples
# get entries too. Whether they're valid records is records.py's job.
def test_scan_includes_broken_files():
    index = scan_example_project()

    assert "docs/sessions/2026-09-21-demo-003-malformed-yaml.md" in index


# Each entry holds the size, the last-changed time, and the
# fingerprint.
def test_scan_entry_has_size_modified_and_hash():
    index = scan_example_project()
    entry = index["docs/sessions/2026-09-21-demo-001-valid-sample.md"]

    assert entry["size"] > 0
    assert entry["modified"] > 0
    assert len(entry["hash"]) > 0


# A folder listed in ridge.yml that doesn't exist yet adds nothing,
# the same rule records.py follows (ADR-0006).
def test_scan_skips_missing_folders(tmp_path):
    config_data = load_config(EXAMPLE_CONFIG_PATH)
    project_location = resolve_project_location(
        EXAMPLE_CONFIG_PATH, config_data["projects"][0]["project_path"]
    )
    marker_file = read_marker(project_location / MARKER_FILE_NAME)
    conventions = marker_file.get("conventions", {})

    index = scan_project(tmp_path, conventions, ["*.md"])

    assert index == {}
