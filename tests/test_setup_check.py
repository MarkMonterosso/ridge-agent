# ============================================================
# test_setup_check.py
# Tests for setup_check.py, the code behind `py main.py --check`.
#
# The first test runs the check on config.example.yml, the same
# file a new user copies to get started. That has to pass, or a
# new user's first step fails.
#
# The rest hand the check a setup that's wrong on purpose and
# make sure it says so. A few of those need a project folder that
# is missing or empty, so they use tmp_path, a throwaway folder
# pytest gives each test.
# ============================================================
from pathlib import Path

from config import load_config
from setup_check import (
    check_config_entry,
    check_marker_file,
    check_project,
    run_setup_check,
)

EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.example.yml"


def levels(findings):
    return [level for level, _ in findings]


# A new user copies config.example.yml and runs the check first.
# It has to come back clean.
def test_setup_check_passes_on_example_config():
    assert run_setup_check(EXAMPLE_CONFIG_PATH) is True


# A project folder without a ridge.yml can't be read at all.
def test_setup_check_reports_missing_marker_file(tmp_path):
    config_path = tmp_path / "config.yml"
    (tmp_path / "empty_project").mkdir()
    project = {"project_path": "empty_project", "data_collection_range": {"weeks": 1}}

    _, findings = check_project(config_path, project)

    assert levels(findings) == ["ERR"]


# A project folder that doesn't exist at all.
def test_setup_check_reports_missing_project_folder(tmp_path):
    config_path = tmp_path / "config.yml"
    project = {"project_path": "not_there", "data_collection_range": {"weeks": 1}}

    _, findings = check_project(config_path, project)

    assert levels(findings) == ["ERR"]


# The old config format listed a project as a bare path. The
# check should say what's missing instead of crashing.
def test_setup_check_reports_old_config_format():
    findings = check_config_entry("../some-project")
    assert levels(findings) == ["ERR"]


# A data_collection_range key timedelta doesn't understand.
def test_setup_check_reports_bad_collection_range():
    project = {"project_path": "x", "data_collection_range": {"fortnights": 1}}
    findings = check_config_entry(project)
    assert levels(findings) == ["ERR"]


# git_repo written but left blank is a mistake (ADR-0006).
def test_setup_check_reports_blank_git_repo(tmp_path):
    marker_file = {"id": "x", "git_repo": None, "conventions": {}}
    findings = check_marker_file(marker_file, tmp_path)
    assert "ERR" in levels(findings)


# No git_repo at all is fine. The project just doesn't track git.
def test_setup_check_allows_missing_git_repo(tmp_path):
    marker_file = {"id": "x", "conventions": {}}
    findings = check_marker_file(marker_file, tmp_path)
    assert "ERR" not in levels(findings)


# A ridge.yml with no id.
def test_setup_check_reports_missing_id(tmp_path):
    marker_file = {"conventions": {}}
    findings = check_marker_file(marker_file, tmp_path)
    assert "ERR" in levels(findings)


# A record file RIDGE would skip shows up as a warning with the
# file's name. The example config's project has
# two broken sample files in it on purpose: one with no date and
# one with broken YAML.
def test_setup_check_lists_skipped_records_as_warnings():
    config_data = load_config(EXAMPLE_CONFIG_PATH)
    _, findings = check_project(EXAMPLE_CONFIG_PATH, config_data["projects"][0])

    warnings = " ".join(message for level, message in findings if level == "WRN")
    assert "ERR" not in levels(findings)
    assert "missing-date" in warnings
    assert "malformed-yaml" in warnings
