# ============================================================
# test_change_index.py
# Tests for change_index.py, the index RIDGE uses to tell what
# changed since the last post (ADR-0008).
#
# The compare_entries tests were written before their code, so each
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
    compare_entries,
    compare_indexes,
    hash_file_text,
    hash_paragraphs,
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


# ---------- hash_paragraphs ----------


# A blank line ends a paragraph, so this text has two.
def test_paragraphs_split_on_blank_lines():
    text = "First paragraph.\n\nSecond paragraph.\n"

    assert len(hash_paragraphs(text)) == 2


# Editing one paragraph changes only that paragraph's fingerprint.
def test_editing_one_paragraph_changes_only_its_hash():
    before = hash_paragraphs("Intro.\n\nM3 is planned.\n\nOutro.\n")
    after = hash_paragraphs("Intro.\n\nM3 is in progress.\n\nOutro.\n")

    assert before[0] == after[0]
    assert before[1] != after[1]
    assert before[2] == after[2]


# Windows and Linux line endings give the same fingerprints, the
# same rule hash_file_text follows.
def test_paragraph_hashes_ignore_line_endings():
    windows_text = "First.\r\n\r\nSecond.\r\n"
    linux_text = "First.\n\nSecond.\n"

    assert hash_paragraphs(windows_text) == hash_paragraphs(linux_text)


# Extra blank lines, or spaces at the start and end of a paragraph,
# don't create empty paragraphs or change a fingerprint.
def test_extra_blank_lines_and_spaces_are_ignored():
    tidy_text = "First.\n\nSecond.\n"
    messy_text = "\n\nFirst.   \n\n\n\n  Second.\n\n\n"

    assert hash_paragraphs(messy_text) == hash_paragraphs(tidy_text)


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


# Each entry also holds the file's header fields, with dates as
# text so the entry can be saved as JSON.
def test_scan_entry_has_header_fields():
    index = scan_example_project()
    entry = index["docs/sessions/2026-09-21-demo-001-valid-sample.md"]

    assert entry["header"]["id"] == "test-2026-09-21-001"
    assert entry["header"]["date"] == "2026-09-21"


# A milestone's state is what RIDGE will compare to spot a
# milestone moving, so it has to be in the entry.
def test_scan_entry_has_milestone_state():
    index = scan_example_project()
    entry = index["docs/milestones/P1-M1-sample-milestone.md"]

    assert entry["header"]["state"] == "done"


# Each entry holds one fingerprint per paragraph of the body. The
# valid sample has a heading and two paragraphs below its header.
def test_scan_entry_has_paragraph_hashes():
    index = scan_example_project()
    entry = index["docs/sessions/2026-09-21-demo-001-valid-sample.md"]

    assert len(entry["paragraphs"]) == 3


# A file with a broken header still gets an entry, with an empty
# header and its paragraphs.
def test_scan_entry_for_broken_header_is_empty():
    index = scan_example_project()
    entry = index["docs/sessions/2026-09-21-demo-003-malformed-yaml.md"]

    assert entry["header"] == {}
    assert len(entry["paragraphs"]) > 0


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


# ---------- compare_indexes ----------
#
# These build small indexes by hand. compare_indexes only looks at
# the entries, so it doesn't need real files.


def entry(file_hash, modified=1.0):
    # One index entry with only the parts compare_indexes looks at.
    return {"size": 10, "modified": modified, "hash": file_hash}


# A file that's only in this run's scan is new.
def test_compare_finds_new_files():
    old_index = {"docs/a.md": entry("aaa")}
    new_index = {"docs/a.md": entry("aaa"), "docs/b.md": entry("bbb")}

    result = compare_indexes(old_index, new_index)

    assert result["new"] == ["docs/b.md"]


# A file that was in the last index but is gone now was deleted.
def test_compare_finds_deleted_files():
    old_index = {"docs/a.md": entry("aaa"), "docs/b.md": entry("bbb")}
    new_index = {"docs/a.md": entry("aaa")}

    result = compare_indexes(old_index, new_index)

    assert result["deleted"] == ["docs/b.md"]


# Same file, different fingerprint, means its text changed.
def test_compare_finds_changed_files():
    old_index = {"docs/a.md": entry("aaa")}
    new_index = {"docs/a.md": entry("zzz")}

    result = compare_indexes(old_index, new_index)

    assert result["changed"] == ["docs/a.md"]


# A new last-changed time with the same fingerprint means the file
# was saved or synced without its words changing. That isn't a
# change.
def test_compare_ignores_a_new_time_with_the_same_text():
    old_index = {"docs/a.md": entry("aaa", modified=1.0)}
    new_index = {"docs/a.md": entry("aaa", modified=99.0)}

    result = compare_indexes(old_index, new_index)

    assert result == {"new": [], "deleted": [], "changed": [], "renamed": []}


# Each list comes back sorted, so the same two indexes always give
# the same result.
def test_compare_lists_are_sorted():
    old_index = {}
    new_index = {
        "docs/c.md": entry("c"),
        "docs/a.md": entry("a"),
        "docs/b.md": entry("b"),
    }

    result = compare_indexes(old_index, new_index)

    assert result["new"] == ["docs/a.md", "docs/b.md", "docs/c.md"]


# The changed list is sorted too. With more than one changed file,
# the order has to be the same every run. Eight files, so an
# unsorted list can't come out in order by luck.
def test_compare_changed_list_is_sorted():
    names = ["h", "c", "f", "a", "g", "b", "e", "d"]
    old_index = {f"docs/{name}.md": entry("before") for name in names}
    new_index = {f"docs/{name}.md": entry("after") for name in names}

    result = compare_indexes(old_index, new_index)

    assert result["changed"] == sorted(old_index)


# A file that disappeared from one path and showed up at another
# with the same fingerprint was moved or renamed. It's reported as
# one rename, old path then new path, and not as a delete plus a
# new file.
def test_compare_finds_renamed_files():
    old_index = {"docs/old-name.md": entry("same")}
    new_index = {"docs/new-name.md": entry("same")}

    result = compare_indexes(old_index, new_index)

    assert result["renamed"] == [["docs/old-name.md", "docs/new-name.md"]]
    assert result["new"] == []
    assert result["deleted"] == []


# If a file was renamed and edited in the same week, the fingerprint
# no longer matches, so there's no way to tell. It stays a delete
# plus a new file.
def test_compare_rename_with_edit_stays_new_and_deleted():
    old_index = {"docs/old-name.md": entry("before")}
    new_index = {"docs/new-name.md": entry("after")}

    result = compare_indexes(old_index, new_index)

    assert result["renamed"] == []
    assert result["new"] == ["docs/new-name.md"]
    assert result["deleted"] == ["docs/old-name.md"]


# ---------- compare_entries ----------


def full_entry(header, paragraphs):
    # One index entry with a header and paragraph fingerprints.
    return {
        "size": 10,
        "modified": 1.0,
        "hash": "x",
        "header": header,
        "paragraphs": paragraphs,
    }


# A milestone moving from in-progress to done shows up as a header
# change, with the old value and the new one.
def test_compare_entries_finds_a_changed_field():
    old_entry = full_entry({"id": "M3", "state": "in-progress"}, [])
    new_entry = full_entry({"id": "M3", "state": "done"}, [])

    result = compare_entries(old_entry, new_entry)

    assert result["header_changes"] == {"state": ["in-progress", "done"]}


# A field that wasn't there before shows None as its old value.
def test_compare_entries_finds_an_added_field():
    old_entry = full_entry({"id": "M3"}, [])
    new_entry = full_entry({"id": "M3", "completed": "2026-10-18"}, [])

    result = compare_entries(old_entry, new_entry)

    assert result["header_changes"] == {"completed": [None, "2026-10-18"]}


# A field that's gone now shows None as its new value.
def test_compare_entries_finds_a_removed_field():
    old_entry = full_entry({"id": "M3", "blocker": "waiting on M2"}, [])
    new_entry = full_entry({"id": "M3"}, [])

    result = compare_entries(old_entry, new_entry)

    assert result["header_changes"] == {"blocker": ["waiting on M2", None]}


# A paragraph added in the middle is reported by its position in
# the new file, so later code can pull its text from the file.
def test_compare_entries_finds_added_paragraphs():
    old_entry = full_entry({}, ["p1", "p2", "p3"])
    new_entry = full_entry({}, ["p1", "new", "p2", "p3"])

    result = compare_entries(old_entry, new_entry)

    assert result["added_paragraphs"] == [1]
    assert result["removed_paragraph_count"] == 0


# A removed paragraph's text is gone from the file, so all RIDGE can
# say is how many were removed.
def test_compare_entries_counts_removed_paragraphs():
    old_entry = full_entry({}, ["p1", "p2", "p3"])
    new_entry = full_entry({}, ["p1", "p3"])

    result = compare_entries(old_entry, new_entry)

    assert result["added_paragraphs"] == []
    assert result["removed_paragraph_count"] == 1


# Moving paragraphs around without changing their words isn't new
# writing, so nothing is reported as added or removed.
def test_compare_entries_ignores_reordered_paragraphs():
    old_entry = full_entry({}, ["p1", "p2"])
    new_entry = full_entry({}, ["p2", "p1"])

    result = compare_entries(old_entry, new_entry)

    assert result["added_paragraphs"] == []
    assert result["removed_paragraph_count"] == 0
