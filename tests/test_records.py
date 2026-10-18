# ============================================================
# test_records.py
# Tests for validate_record, discover_records,
# find_duplicate_records and read_header_and_body in records.py.
#
# The read_header_and_body tests were written before their code,
# so each one is marked as an expected failure until it passes.
#
# The discover_records tests don't make up their own folders.
# They read config.example.yml, follow it to the project it
# lists, read that project's ridge.yml, and look in whatever
# folders it lists. That's the same path RIDGE takes on a real
# run, so if the config and the code stop matching, these tests
# break.
#
# The example config points at a sample project whose files only
# change when someone changes them on purpose, so these tests can
# look for specific sample records by id.
#
# validate_record and find_duplicate_records still get plain
# dictionaries. Neither one reads files, so there's no folder
# for them to depend on.
# ============================================================
from datetime import date
from pathlib import Path

import pytest

from ridge.config import (
    MARKER_FILE_NAME,
    load_config,
    read_marker,
    resolve_project_location,
)
from ridge.records import (
    DEFAULT_INCLUDED_PATTERNS,
    discover_records,
    find_duplicate_records,
    read_header_and_body,
    resolve_included_patterns,
    validate_record,
)

# The example config sits at the top of the repo, one folder up
# from this file.
EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.example.yml"


def load_example_projects():
    # Read the example config and each project's marker file the
    # same way main.py does. Returns a list of
    # (project_location, marker_file) pairs.
    config_data = load_config(EXAMPLE_CONFIG_PATH)
    projects = []
    for project in config_data["projects"]:
        project_location = resolve_project_location(
            EXAMPLE_CONFIG_PATH, project["project_path"]
        )
        marker_file = read_marker(project_location / MARKER_FILE_NAME)
        projects.append((project_location, marker_file))
    return projects


def read_project_records():
    # Uses the first project in the example config. The id checks
    # below are written against that project's sample files, so
    # they only look at that one.
    project_location, marker_file = load_example_projects()[0]
    conventions = marker_file.get("conventions", {})
    included_patterns = resolve_included_patterns(marker_file, project_location)
    return discover_records(project_location, conventions, included_patterns)


def find_record(records, record_id):
    for record in records:
        if record.get("id") == record_id:
            return record
    return None


# ---------- resolve_included_patterns ----------


# No included_patterns in ridge.yml means the project didn't set
# one, so RIDGE uses its built-in default (ADR-0006, state 1).
def test_resolve_included_patterns_uses_default_when_missing():
    assert (
        resolve_included_patterns({}, "some/project/location")
        == DEFAULT_INCLUDED_PATTERNS
    )


# included_patterns written with nothing after the colon. YAML
# reads that as None. Someone set the key and left it unfinished,
# so RIDGE stops (ADR-0006, state 2).
def test_resolve_included_patterns_stops_when_none():
    with pytest.raises(SystemExit):
        resolve_included_patterns({"included_patterns": None}, "some/project/location")


# The other way to leave it blank: an empty string.
def test_resolve_included_patterns_stops_when_empty_string():
    with pytest.raises(SystemExit):
        resolve_included_patterns({"included_patterns": ""}, "some/project/location")


# A real list comes back as it was written.
def test_resolve_included_patterns_returns_the_list():
    patterns = ["*.md", "*.txt"]
    assert (
        resolve_included_patterns(
            {"included_patterns": patterns}, "some/project/location"
        )
        == patterns
    )


# ---------- validate_record ----------


# A record with no id can't be pointed at or checked for
# duplicates later, so it gets rejected.
def test_validate_record_missing_id():
    metadata = {"type": "session", "date": date(2026, 1, 1)}
    assert validate_record(metadata) is not None


# Having the id key isn't enough. It needs a value.
def test_validate_record_blank_id():
    metadata = {"type": "session", "id": None, "date": date(2026, 1, 1)}
    assert validate_record(metadata) is not None


# A session with an id and a real date passes.
def test_validate_record_valid_session():
    metadata = {"type": "session", "id": "2026-01-01-001", "date": date(2026, 1, 1)}
    assert validate_record(metadata) is None


# A session needs a date to land in the right week.
def test_validate_record_session_without_date():
    metadata = {"type": "session", "id": "2026-01-01-001"}
    assert validate_record(metadata) is not None


# An unfilled template leaves the date as the text "YYYY-MM-DD".
# YAML only turns a real date into a date object, so this text
# should be rejected.
def test_validate_record_placeholder_date():
    metadata = {"type": "session", "id": "YYYY-MM-DD-NNN", "date": "YYYY-MM-DD"}
    assert validate_record(metadata) is not None


# Milestone records don't have a date. They use "completed"
# instead (ADR-0002, ADR-0004), so a missing date is normal for
# them.
def test_validate_record_milestone_without_date():
    metadata = {
        "type": "milestone",
        "id": "M1",
        "title": "A milestone",
        "state": "done",
        "order": 1,
        "completed": date(2026, 1, 1),
        "phase": 5,
    }
    assert validate_record(metadata) is None


# ---------- the example config ----------


# The example config has to point at a project RIDGE can read.
# If someone changes it to a path that only exists on their own
# machine, this is the test that catches it.
def test_example_config_points_at_a_readable_project():
    projects = load_example_projects()
    assert len(projects) > 0
    for project_location, marker_file in projects:
        assert project_location.is_dir()
        assert "conventions" in marker_file


# ---------- discover_records ----------


# A complete, valid session gets read.
def test_discover_records_reads_valid_session():
    records = read_project_records()
    assert find_record(records, "test-2026-09-21-001") is not None


# A session with no date gets left out.
def test_discover_records_skips_session_without_date():
    records = read_project_records()
    assert find_record(records, "test-2026-09-21-002") is None


# A session with broken YAML gets left out, and the rest of the
# project still gets read in the same call.
def test_discover_records_skips_malformed_yaml():
    records = read_project_records()
    assert find_record(records, "test-2026-09-21-003") is None
    assert find_record(records, "test-2026-09-21-001") is not None


# A decision gets read. Its file says type: decision.
def test_discover_records_reads_decision():
    records = read_project_records()
    decisions = [record for record in records if record.get("type") == "decision"]
    assert len(decisions) == 1


# A milestone has no date, like every real milestone
# record, and it should still get read.
def test_discover_records_reads_milestone_without_date():
    records = read_project_records()
    milestone = find_record(records, "M1")
    assert milestone is not None
    assert milestone.get("type") == "milestone"


# This session has no type line, so RIDGE has to work out its
# type from the folder it sits in. The folder's entry in ridge.yml
# is named after the type, so that name is the answer. Phase 1
# calls this the second step of the type ladder.
def test_discover_records_type_comes_from_folder_when_file_has_none():
    records = read_project_records()
    record = find_record(records, "test-2026-09-21-005")
    assert record is not None
    assert record.get("type") == "session"


# People write ids however they like, without quotes. YAML reads
# id: 0001 as the number 1 and drops the zeros, so RIDGE has to
# keep ids as text while it reads the file. Changing the number
# back to text afterward only gives "1".
def test_discover_records_keeps_ids_as_text():
    records = read_project_records()
    assert find_record(records, "0001") is not None
    for record in records:
        assert isinstance(record.get("id"), str)


# This file says type: session but sits in the decisions
# folder. When a file says what it is, RIDGE believes the file
# (step one of Phase 1's type ladder). Without this test, a change
# that checked the folder first would go unnoticed.
def test_discover_records_file_type_beats_folder():
    records = read_project_records()
    record = find_record(records, "test-2026-09-21-004")
    assert record is not None
    assert record.get("type") == "session"


# Every record that comes back should know what type it is.
# Nothing after this point can count sessions or diff milestones
# without that.
def test_discover_records_every_record_has_a_type():
    records = read_project_records()
    assert len(records) > 0
    for record in records:
        assert record.get("type")


# A folder named in ridge.yml that doesn't exist yet is normal
# for a new project (ADR-0006). This uses the project's real marker
# file but an empty project folder, so every folder it lists is
# missing. RIDGE should return nothing and keep going.
def test_discover_records_missing_folders(tmp_path):
    _, marker_file = load_example_projects()[0]
    conventions = marker_file.get("conventions", {})
    included_patterns = resolve_included_patterns(marker_file, tmp_path)
    records = discover_records(tmp_path, conventions, included_patterns)
    assert records == []


# This sample file has a complete header and would be accepted if
# RIDGE read it. It's a .txt file, and the example project doesn't
# allow .txt, so it never gets read.
def test_discover_records_skips_files_not_in_included_patterns():
    records = read_project_records()
    assert find_record(records, "test-2026-09-21-006") is None


# included_patterns can list more than one pattern. With both "*.md"
# and "*.txt" allowed, the .txt sample that is skipped by default
# gets read too.
def test_discover_records_reads_every_listed_pattern():
    project_location, marker_file = load_example_projects()[0]
    conventions = marker_file.get("conventions", {})
    records = discover_records(project_location, conventions, ["*.md", "*.txt"])
    assert find_record(records, "test-2026-09-21-006") is not None
    assert find_record(records, "test-2026-09-21-001") is not None


# No two records in a project share an id.
def test_discover_records_finds_no_duplicate_ids():
    records = read_project_records()
    assert find_duplicate_records(records) == []


# ---------- read_header_and_body ----------


# The header fields and the text below them come back separately.
def test_header_and_body_come_back_separately(tmp_path):
    record_file = tmp_path / "session.md"
    record_file.write_text(
        "---\ntype: session\nid: test-001\n---\n\nFirst paragraph.\n",
        encoding="utf-8",
    )

    header, body = read_header_and_body(record_file)

    assert header["type"] == "session"
    assert header["id"] == "test-001"
    assert body.strip() == "First paragraph."


# Headers are optional. A plain note gives an empty header and its
# whole text as the body.
def test_file_without_header_gives_empty_header(tmp_path):
    plain_file = tmp_path / "note.md"
    plain_file.write_text("Just a plain note.\n", encoding="utf-8")

    header, body = read_header_and_body(plain_file)

    assert header == {}
    assert body.strip() == "Just a plain note."


# A broken header doesn't stop the scan. The file still gets an
# entry, with an empty header and its whole text as the body.
def test_broken_header_gives_empty_header(tmp_path):
    broken_file = tmp_path / "broken.md"
    broken_file.write_text("---\nid: [unclosed\n---\nBody.\n", encoding="utf-8")

    header, body = read_header_and_body(broken_file)

    assert header == {}
    assert "Body." in body


# Dates come back as text, because the index is saved as JSON.
def test_header_dates_come_back_as_text(tmp_path):
    record_file = tmp_path / "session.md"
    record_file.write_text(
        "---\nid: test-001\ndate: 2026-10-18\n---\n", encoding="utf-8"
    )

    header, _body = read_header_and_body(record_file)

    assert header["date"] == "2026-10-18"


# Ids keep their leading zeros, the same rule discover_records
# follows.
def test_header_ids_stay_text(tmp_path):
    record_file = tmp_path / "decision.md"
    record_file.write_text("---\nid: 0001\n---\n", encoding="utf-8")

    header, _body = read_header_and_body(record_file)

    assert header["id"] == "0001"


# ---------- find_duplicate_records ----------


# The second record with an id we've already seen gets flagged.
# The first one doesn't.
def test_find_duplicate_records_detects_duplicate():
    records = [
        {"id": "001", "title": "First"},
        {"id": "002", "title": "Second"},
        {"id": "001", "title": "Third, same id as First"},
    ]

    duplicates = find_duplicate_records(records)

    assert len(duplicates) == 1
    assert duplicates[0]["title"] == "Third, same id as First"


# No shared ids means nothing gets flagged.
def test_find_duplicate_records_no_duplicates():
    records = [{"id": "001"}, {"id": "002"}, {"id": "003"}]
    assert find_duplicate_records(records) == []
