# ============================================================
# main.py
# Entry point for RIDGE.
#
# Reads config.yml to find every project to track. For each one:
# reads that project's ridge.yml marker file once, walks its
# archive and reads every record it finds (validating each one
# and flagging any duplicate ids), and checks whether that project
# has git_repo set — if it does, reports its recent commit activity
# for the configured lookback window.
#
# Not built yet: writing the generated field note back out.
# ============================================================
import argparse
from datetime import timedelta
from pathlib import Path

from config import load_config, read_marker
from git_history import get_git_history, resolve_git_repo_path
from records import discover_records, find_duplicate_records

if __name__ == "__main__":
    # --config lets you point at a different config file. Left
    # unset, it defaults to config.yml in the current folder.
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yml")
    args = parser.parse_args()

    config_data = load_config(args.config)

    # Every project in the list gets the exact same treatment, one
    # at a time. A problem with one project (handled inside the
    # functions this loop calls) still stops the whole run for now —
    # that's an open question, not a decision made here.
    for project in config_data["projects"]:
        project_location = project["project_path"]
        lookback = timedelta(**project["data_collection_range"])

        marker_path = Path(project_location) / "ridge.yml"
        marker_file = read_marker(marker_path)
        conventions = marker_file.get("conventions", {})
        records = discover_records(project_location, conventions)
        duplicate_ids = find_duplicate_records(records)

        git_repo_path = resolve_git_repo_path(marker_file, project_location)

        if git_repo_path:
            commits = get_git_history(str(git_repo_path), lookback)
            print(f"Found {len(commits)} commit(s) in the last {lookback}.")

        # A short, human-readable summary of the run — not the full record
        # dump. This is a manual smoke check against your real archive,
        # not a substitute for running the test suite.
        print(
            f"Discovered {len(records)} valid records in project at {project_location}."
        )
        if duplicate_ids:
            print(
                f"Found {len(duplicate_ids)} duplicate id(s): {[r.get('id') for r in duplicate_ids]}"
            )
        else:
            print("No duplicate ids found.")
