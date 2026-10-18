# ============================================================
# setup_check.py
# Checks whether RIDGE is set up right, without running it.
# This is what `py main.py --check` runs.
#
# For each project in config.yml it checks that the project
# folder and its ridge.yml exist, that ridge.yml has what RIDGE
# needs, and which record files RIDGE would keep or skip.
#
# Each finding has a level, using the same tags as the rest of
# RIDGE's output:
#   [ERR]  RIDGE can't run until this is fixed
#   [WRN]  RIDGE will run, but you should look at this
#   [INF]  just so you know
#
# A record file RIDGE would skip is only a [WRN]. A bad record
# doesn't stop the run, and the demo project has two broken files
# in it on purpose.
# ============================================================
from collections import Counter
from datetime import timedelta

import yaml
from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from ridge.config import MARKER_FILE_NAME, load_config, resolve_project_location
from ridge.file_io import open_utf8_file
from ridge.records import (
    DEFAULT_INCLUDED_PATTERNS,
    find_duplicate_records,
    read_records,
)


def check_marker_file(marker_file, project_location):
    findings = []

    if not marker_file.get("id"):
        findings.append(("ERR", "ridge.yml has no id."))

    # git_repo follows ADR-0006. Left out means this project doesn't
    # track git, which is fine. Present but blank, or pointing
    # somewhere that isn't a git repo, is a mistake.
    if "git_repo" not in marker_file:
        findings.append(("INF", "No git_repo set, so git history won't be read."))
    elif not marker_file.get("git_repo"):
        findings.append(("ERR", "git_repo is in ridge.yml but has no value."))
    else:
        git_repo_path = (project_location / marker_file["git_repo"]).resolve()
        try:
            Repo(git_repo_path)
            findings.append(("INF", f"git_repo found at {git_repo_path}"))
        except (InvalidGitRepositoryError, NoSuchPathError):
            findings.append(("ERR", f"git_repo isn't a git repo: {git_repo_path}"))

    # included_patterns follows ADR-0006 too. Left out means the
    # default is used. Present but blank is a mistake.
    if "included_patterns" not in marker_file:
        findings.append(
            (
                "INF",
                f"No included_patterns set, so default patterns '{DEFAULT_INCLUDED_PATTERNS}' will be used.",
            )
        )
    elif not marker_file.get("included_patterns"):
        findings.append(("ERR", "included_patterns is in ridge.yml but has no value."))

    # conventions follows ADR-0006 too. Left out means no records
    # get read. A blank entry is a mistake. A folder that doesn't
    # exist yet is normal for a new project.
    conventions = marker_file.get("conventions")
    if conventions is None:
        findings.append(("WRN", "No conventions set, so no records will be read."))
        return findings
    for record_type, folder_path in conventions.items():
        if not folder_path:
            findings.append(("ERR", f"The folder for '{record_type}' is blank."))
        elif not (project_location / folder_path).exists():
            findings.append(
                (
                    "WRN",
                    f"The folder for '{record_type}' doesn't exist yet: {folder_path}",
                )
            )
    return findings


def check_records(project_location, conventions, included_patterns):
    findings = []
    # Skip any blank entries here. check_marker_file() already
    # reported them.
    usable_conventions = {
        record_type: folder_path
        for record_type, folder_path in conventions.items()
        if folder_path
    }
    kept_records, rejected_files = read_records(
        project_location, usable_conventions, included_patterns
    )

    counts_by_type = Counter(record.get("type") for record in kept_records)
    counts_text = ", ".join(
        f"{count} {record_type}"
        for record_type, count in sorted(counts_by_type.items())
    )
    findings.append(
        ("INF", f"{len(kept_records)} records would be read ({counts_text or 'none'}).")
    )

    for record_file, reason in rejected_files:
        relative_path = record_file.relative_to(project_location)
        findings.append(("WRN", f"Would skip {relative_path}: {reason}"))

    for duplicate in find_duplicate_records(kept_records):
        findings.append(
            ("WRN", f"More than one record has the id {duplicate.get('id')}.")
        )
    return findings


def check_config_entry(project):
    # An older config format listed each project as a bare path.
    # The current one needs project_path and data_collection_range.
    if not isinstance(project, dict) or not project.get("project_path"):
        return [("ERR", "This project entry has no project_path.")]
    collection_range = project.get("data_collection_range")
    if not isinstance(collection_range, dict):
        return [("ERR", "This project entry has no data_collection_range.")]
    try:
        timedelta(**collection_range)
    except TypeError:
        return [
            (
                "ERR",
                f"data_collection_range has a key timedelta doesn't accept: {collection_range}",
            )
        ]
    return []


def check_project(config_path, project):
    entry_findings = check_config_entry(project)
    if entry_findings:
        return project, entry_findings

    project_location = resolve_project_location(config_path, project["project_path"])
    if not project_location.is_dir():
        return project_location, [("ERR", "This folder doesn't exist.")]

    marker_path = project_location / MARKER_FILE_NAME
    if not marker_path.is_file():
        return project_location, [("ERR", f"No {MARKER_FILE_NAME} in this folder.")]

    # Read ridge.yml here instead of with read_marker(), because
    # read_marker() stops the whole program on a bad file. The check
    # should report the problem and move on to the next project.
    try:
        with open_utf8_file(marker_path) as marker_contents:
            marker_file = yaml.safe_load(marker_contents) or {}
    except yaml.YAMLError as err:
        return project_location, [
            (
                "ERR",
                f"{MARKER_FILE_NAME} isn't valid YAML: {' '.join(str(err).split())}",
            )
        ]

    findings = check_marker_file(marker_file, project_location)
    conventions = marker_file.get("conventions") or {}
    included_patterns = (
        marker_file.get("included_patterns") or DEFAULT_INCLUDED_PATTERNS
    )
    findings += check_records(project_location, conventions, included_patterns)
    return project_location, findings


def run_setup_check(config_path):
    # load_config() stops the program with its own message if
    # config.yml is missing, isn't valid YAML, or lists no projects.
    # Any of those means there's nothing else to check.
    config_data = load_config(config_path)
    print(f"Checking {config_path}")

    error_count = 0
    for project in config_data["projects"]:
        project_location, findings = check_project(config_path, project)
        print(f"\nProject: {project_location}")
        for level, message in findings:
            print(f"  [{level}] {message}")
        error_count += sum(1 for level, _ in findings if level == "ERR")

    if error_count:
        print(
            f"\nFound {error_count} problem(s) marked [ERR]. RIDGE can't run until they're fixed."
        )
    else:
        print("\nSetup looks good. RIDGE is ready to run.")
    return error_count == 0
