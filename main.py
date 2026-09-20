# ============================================================
# main.py
# Entry point for RIDGE.
#
# Reads config.yml to find where a project's archive lives, reads
# that project's ridge.yml marker file, then walks the archive and
# reads every record it finds, validating each one and flagging
# any duplicate ids.
#
# Not built yet: reading the project's git history (M2), and
# writing the generated field note back out (M6).
# ============================================================
import argparse
from pathlib import Path

from config import load_config, read_marker
from records import discover_records, find_duplicate_records

if __name__ == "__main__":
    # --config lets you point at a different config file. Left
    # unset, it defaults to config.yml in the current folder.
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yml")
    args = parser.parse_args()

    # Only the first project in the list is used for now. Tracking
    # more than one project at once comes later.
    config_data = load_config(args.config)
    project_location = config_data["projects"][0]
    marker_path = Path(project_location) / "ridge.yml"
    conventions = read_marker(marker_path)["conventions"]
    records = discover_records(project_location, conventions)
    duplicate_ids = find_duplicate_records(records)

    # A short, human-readable summary of the run — not the full record
    # dump. This is a manual smoke check against your real archive,
    # not a substitute for the unit tests in test_main.py.
    print(f"Discovered {len(records)} valid records in project at {project_location}.")
    if duplicate_ids:
        print(f"Found {len(duplicate_ids)} duplicate id(s): {[r.get('id') for r in duplicate_ids]}")
    else:
        print("No duplicate ids found.")
