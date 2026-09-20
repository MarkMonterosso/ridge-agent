# ============================================================
# test_records.py
# Tests for validate_record, discover_records, and
# find_duplicate_records in records.py.
#
# validate_record and find_duplicate_records are tested with
# plain dictionaries — neither one touches a file, so neither
# needs one. discover_records is tested with real markdown files
# built under tmp_path, since its whole job is reading them.
# ============================================================
from datetime import date

from records import discover_records, find_duplicate_records, validate_record


# A record missing its id entirely should fail validation.
def test_validate_record_missing_id():
    metadata = {"date": date(2026, 1, 1)}
    assert validate_record(metadata) is not None


# A record whose id key is present but blank should also fail —
# having the key isn't enough, it needs a real value.
def test_validate_record_blank_id():
    metadata = {"id": None, "date": date(2026, 1, 1)}
    assert validate_record(metadata) is not None


# A record with a real id and a real date should pass.
def test_validate_record_valid():
    metadata = {"id": "2026-01-01-001", "date": date(2026, 1, 1)}
    assert validate_record(metadata) is None


# A date that's still plain text, like an unfilled "YYYY-MM-DD"
# template placeholder, should fail — PyYAML only turns a real
# date into a date object, never plain text like this.
def test_validate_record_placeholder_date():
    metadata = {"id": "YYYY-MM-DD-NNN", "date": "YYYY-MM-DD"}
    assert validate_record(metadata) is not None


# discover_records should find a well-formed record and include
# it in the list it returns.
def test_discover_records_valid_record(tmp_path):
    sessions_dir = tmp_path / "docs" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "2026-01-01-001.md").write_text(
        "---\nid: 2026-01-01-001\ndate: 2026-01-01\ntitle: A session\n---\nBody text.\n",
        encoding="utf-8",
    )

    records = discover_records(tmp_path, {"session": "docs/sessions"})

    assert len(records) == 1
    assert records[0]["id"] == "2026-01-01-001"


# A record with malformed YAML in its frontmatter should be skipped
# and logged, the same as a record that fails validation — not
# treated as fatal for the whole archive read.
def test_discover_records_skips_malformed_yaml(tmp_path):
    sessions_dir = tmp_path / "docs" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "good.md").write_text(
        '---\nid: "001"\ndate: 2026-01-01\n---\nBody.\n', encoding="utf-8"
    )
    (sessions_dir / "bad.md").write_text(
        "---\nid: [unclosed\ndate: 2026-01-01\n---\nBody.\n", encoding="utf-8"
    )

    records = discover_records(tmp_path, {"session": "docs/sessions"})

    assert len(records) == 1
    assert records[0]["id"] == "001"


# A conventions folder that doesn't exist yet shouldn't crash the
# program — a project may simply not have any records of that
# type written yet.
def test_discover_records_missing_folder(tmp_path):
    records = discover_records(tmp_path, {"session": "docs/sessions"})
    assert records == []


# A record that fails validation (missing id here) should be
# logged and skipped, not included in the returned list.
def test_discover_records_skips_invalid_record(tmp_path):
    sessions_dir = tmp_path / "docs" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "no_id.md").write_text(
        "---\ndate: 2026-01-01\n---\nBody.\n", encoding="utf-8"
    )

    records = discover_records(tmp_path, {"session": "docs/sessions"})

    assert records == []


# find_duplicate_records should flag a later record that shares
# an id already seen, but not the first occurrence of that id.
def test_find_duplicate_records_detects_duplicate():
    records = [
        {"id": "001", "title": "First"},
        {"id": "002", "title": "Second"},
        {"id": "001", "title": "Third, same id as First"},
    ]

    duplicates = find_duplicate_records(records)

    assert len(duplicates) == 1
    assert duplicates[0]["title"] == "Third, same id as First"


# No shared ids means no duplicates found.
def test_find_duplicate_records_no_duplicates():
    records = [{"id": "001"}, {"id": "002"}, {"id": "003"}]
    assert find_duplicate_records(records) == []
