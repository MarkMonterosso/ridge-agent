# ============================================================
# main.py
# Entry point for RIDGE.
#
# Right now, this reads config.yml to find where a project's
# archive lives, then reads and parses that project's ridge.yml
# marker file. Any problem along the way, a missing file, no
# permission to read it, or YAML that doesn't parse, stops the
# program with a clear message instead of guessing or crashing
# with a raw traceback.
#
# Not built yet: actually looking inside the archive's folders
# (sessions, decisions) and reading what's in them.
# ============================================================
import argparse
import sys
from pathlib import Path
import yaml


def load_config(config_path):
    # Read the config file. Stop clearly if it's missing or unreadable.
    try:
        with open(config_path) as config_file:
            config_contents = config_file.read()
    except FileNotFoundError:
        print(f"Config file not found: {config_path}")
        sys.exit(1)
    except PermissionError:
        print(f"Permission denied when trying to read config file: {config_path}")
        sys.exit(1)

    # Turn the config text into a usable dictionary. Stop clearly if
    # the YAML in it doesn't actually parse.
    try:
        config_data = yaml.safe_load(config_contents)
    except yaml.YAMLError as err:
        print(f"Error parsing config file: {err}")
        sys.exit(1)

    # Stop clearly if the config has no projects listed at all.
    if "projects" not in config_data or not config_data["projects"]:
        print("No projects found in the configuration file.")
        sys.exit(1)

    return config_data


def read_marker(marker_path):
    # Read that project's marker file. Stop clearly if it's missing
    # or unreadable.
    try:
        with open(marker_path) as marker_file:
            marker_contents = marker_file.read()
    except FileNotFoundError:
        print(f"Marker file not found: {marker_path}")
        sys.exit(1)
    except PermissionError:
        print(f"Permission denied when trying to read marker file: {marker_path}")
        sys.exit(1)

    # Turn the marker text into a usable dictionary. Stop clearly if
    # the YAML in it doesn't actually parse.
    try:
        marker_data = yaml.safe_load(marker_contents)
    except yaml.YAMLError as err:
        print(f"Error parsing marker file: {err}")
        sys.exit(1)

    return marker_data


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

    print(read_marker(marker_path))
