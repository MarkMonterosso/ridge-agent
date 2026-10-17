# ============================================================
# main.py
# Entry point for RIDGE.
#
# With --check, it only checks the setup and reports what it
# finds (see setup_check.py). Nothing else runs.
#
# Without --check, it reads config.yml to find every project to
# track. For each one it reads that project's ridge.yml once,
# reads every record in the folders it lists, flags duplicate
# ids, and, if git_repo is set, reports recent commit activity
# for the configured lookback window.
#
# Not built yet: writing the field note back out.
# ============================================================
import argparse
import sys
from datetime import timedelta

from config import (
    MARKER_FILE_NAME,
    load_config,
    read_marker,
    resolve_project_location,
)
from git_history import get_git_history, resolve_git_repo_path
from records import discover_records, find_duplicate_records
from setup_check import run_setup_check

if __name__ == "__main__":
    # --config points at a different config file. Left unset, it
    # uses config.yml in the current folder.
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yml")
    parser.add_argument(
        "--check",
        action="store_true",
        help="check the setup and report problems, without running RIDGE",
    )
    args = parser.parse_args()

    if args.check:
        # Exit code 1 when there's a problem, so a script or a
        # scheduled task can tell the check didn't pass.
        setup_is_good = run_setup_check(args.config)
        sys.exit(0 if setup_is_good else 1)

    config_data = load_config(args.config)

    # Every project gets the same steps, one at a time. A problem
    # with one project still stops the whole run for now. How that
    # should work is an open question tracked in M9.
    for project in config_data["projects"]:
        project_location = resolve_project_location(
            args.config, project["project_path"]
        )
        lookback = timedelta(**project["data_collection_range"])

        marker_file = read_marker(project_location / MARKER_FILE_NAME)
        conventions = marker_file.get("conventions", {})
        records = discover_records(project_location, conventions)
        duplicate_ids = find_duplicate_records(records)

        git_repo_path = resolve_git_repo_path(marker_file, project_location)

        if git_repo_path:
            commits = get_git_history(str(git_repo_path), lookback)
            print(f"Found {len(commits)} commit(s) in the last {lookback}.")

        # A short summary to check by eye against your own archive.
        # It doesn't replace running the tests.
        print(
            f"Discovered {len(records)} valid records in project at {project_location}."
        )
        if duplicate_ids:
            print(
                f"Found {len(duplicate_ids)} duplicate id(s): {[r.get('id') for r in duplicate_ids]}"
            )
        else:
            print("No duplicate ids found.")
