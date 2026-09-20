# ============================================================
# config.py
# Reads RIDGE's own config.yml (which projects to track) and a
# tracked project's ridge.yml marker file (where that project's
# records live). Any problem along the way, a missing file, no
# permission to read it, or YAML that doesn't parse, stops the
# program with a clear message instead of guessing or crashing
# with a raw traceback.
# ============================================================
import sys

import yaml

from file_io import open_utf8_file


def load_config(config_path):
    # Read the config file. Stop clearly if it's missing or unreadable.
    try:
        with open_utf8_file(config_path) as config_file:
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
        with open_utf8_file(marker_path) as marker_file:
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
