# ============================================================
# test_change_index.py
# Tests for change_index.py, the index RIDGE uses to tell what
# changed since the last post (ADR-0008).
#
# The save and load tests were written before their code, so each
# one is marked as an expected failure. When a test starts passing,
# pytest reports it as FAILED with XPASS(strict). That's the cue to
# delete the marker line above it.
#
# The scan tests and the save-then-load test read
# config.example.yml and the demo project, the same way
# test_records.py does. The other tests only need a place to write
# files, so they use tmp_path, an empty throwaway folder pytest
# gives each test.
# ============================================================
from pathlib import Path

import pytest

from ridge.change_index import (
    hash_file_text,
    index_path_for,
    load_index,
    save_index,
    scan_project,
)
from ridge.config import (
    MARKER_FILE_NAME,
    load_config,
    read_marker,
    resolve_project_location,
)
from ridge.records import resolve_included_patterns

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


# ---------- index_path_for ----------


# Each project's index file is named after its id, so two projects
# never share one, and renaming a project folder doesn't lose it.
def test_index_path_is_named_after_project_id(tmp_path):
    index_path = index_path_for(tmp_path, "ridge-agent-demo")

    assert index_path.parent == tmp_path
    assert "ridge-agent-demo" in index_path.name


# ---------- save_index and load_index ----------


# Saving an index and loading it back gives the same index.
def test_save_then_load_gives_back_the_same_index(tmp_path):
    index = scan_example_project()
    index_path = tmp_path / "ridge-agent-demo.index.json"

    save_index(index, index_path)

    assert load_index(index_path) == index


# No index file yet means this is the project's first run.
def test_load_returns_none_when_there_is_no_index(tmp_path):
    assert load_index(tmp_path / "missing.index.json") is None


# The folder that holds the index may not exist yet on a new
# install, so saving creates it.
def test_save_creates_the_folder_if_missing(tmp_path):
    index_path = tmp_path / "state" / "ridge-agent-demo.index.json"

    save_index({}, index_path)

    assert index_path.is_file()


# Saving twice keeps only the newest index.
def test_save_replaces_the_old_index(tmp_path):
    index_path = tmp_path / "ridge-agent-demo.index.json"
    old_index = {"docs/a.md": {"size": 1, "modified": 1.0, "hash": "old"}}
    new_index = {"docs/a.md": {"size": 2, "modified": 2.0, "hash": "new"}}

    save_index(old_index, index_path)
    save_index(new_index, index_path)

    assert load_index(index_path) == new_index


# After a save, only the index file is left in the folder. The
# temporary file used during the write is gone.
def test_save_leaves_no_temporary_file_behind(tmp_path):
    index_path = tmp_path / "ridge-agent-demo.index.json"

    save_index({}, index_path)

    assert [path.name for path in tmp_path.iterdir()] == [index_path.name]


# A damaged index file stops the program with a message, so nobody
# mistakes it for a first run and posts the whole project history.
def test_load_stops_on_a_damaged_index(tmp_path):
    index_path = tmp_path / "ridge-agent-demo.index.json"
    index_path.write_text("{ this is not valid json", encoding="utf-8")

    with pytest.raises(SystemExit):
        load_index(index_path)
