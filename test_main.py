# ============================================================
# test_main.py
# Tests for the functions in main.py: load_config and
# read_marker. Covers a missing file, bad YAML, and the happy
# path for each, plus load_config's extra check for a missing
# "projects" key.
# ============================================================
import pytest
from main import load_config
from main import read_marker


# load_config should stop the program if the file it's given
# doesn't exist, rather than crashing with an unhandled error.
def test_load_config_missing_file():
    with pytest.raises(SystemExit):
        load_config("nonexistent.yml")


# load_config should stop the program if the file exists but
# isn't valid YAML, rather than crashing with a raw traceback.
def test_load_config_yaml_error(tmp_path):
    config_file = tmp_path / "invalid_config.yml"
    config_file.write_text("invalid_yaml: [unclosed_list")

    with pytest.raises(SystemExit):
        load_config(config_file)


# load_config should stop the program if the YAML parses fine
# but never actually lists any projects.
def test_load_config_no_projects(tmp_path):
    config_file = tmp_path / "no_projects.yml"
    config_file.write_text("some_key: some_value")

    with pytest.raises(SystemExit):
        load_config(config_file)


# load_config should return the parsed data as-is when the
# file is valid and actually lists a project.
def test_load_config_valid(tmp_path):
    config_file = tmp_path / "valid_config.yml"
    config_file.write_text("projects:\n  - ../path-to-your-project-archive")

    config_data = load_config(config_file)
    assert "projects" in config_data
    assert config_data["projects"] == ["../path-to-your-project-archive"]


# read_marker should stop the program if the marker file it's
# given doesn't exist.
def test_read_marker_missing_file():
    with pytest.raises(SystemExit):
        read_marker("nonexistent_marker.yml")


# read_marker should stop the program if the marker file
# exists but isn't valid YAML.
def test_read_marker_yaml_error(tmp_path):
    marker_file = tmp_path / "invalid_marker.yml"
    marker_file.write_text("invalid_yaml: [unclosed_list")

    with pytest.raises(SystemExit):
        read_marker(marker_file)


# read_marker should return the parsed data as-is when the
# marker file is valid.
def test_read_marker_valid(tmp_path):
    marker_file = tmp_path / "valid_marker.yml"
    marker_file.write_text("some_key: some_value")

    marker_data = read_marker(marker_file)
    assert marker_data == {"some_key": "some_value"}
