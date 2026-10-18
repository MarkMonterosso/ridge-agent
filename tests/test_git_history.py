# ============================================================
# test_git_history.py
# Tests for get_git_history and resolve_git_repo_path in
# git_history.py.
#
# get_git_history only runs once git_repo is known to be set, so
# failing to reach that repo is a setup mistake and the program
# should stop. Those tests use tmp_path, an empty throwaway folder
# pytest gives each test, so they never touch a real repo and never
# depend on its real commit history.
#
# resolve_git_repo_path decides whether get_git_history gets called
# at all. No git_repo key is fine, since not every project tracks
# git history, so that case returns None. A git_repo key left blank,
# as an empty string or with nothing after the colon, is a setup
# mistake either way, so both stop the program.
# ============================================================
from datetime import timedelta

import pytest
from git import Repo

from git_history import get_git_history, resolve_git_repo_path


# A path that exists but has no .git folder isn't a usable repo.
# Once git_repo is set, that's a setup mistake, so the program
# should stop and say so.
def test_get_git_history_exits_on_non_git_folder(tmp_path):
    with pytest.raises(SystemExit):
        get_git_history(str(tmp_path), timedelta(weeks=1))


# A path that doesn't exist at all is the same kind of mistake,
# and should also stop the program.
def test_get_git_history_exits_on_missing_path(tmp_path):
    missing_path = tmp_path / "does_not_exist"
    with pytest.raises(SystemExit):
        get_git_history(str(missing_path), timedelta(weeks=1))


# GitPython needs a real repo to work with, so make one. This
# is a throwaway repo in a throwaway folder, so it doesn't matter that it's empty and has no commits yet.
def test_get_git_history_returns_commits(tmp_path):

    test_repo_path = tmp_path / "test_repo"
    test_repo_path.mkdir()

    test_file = test_repo_path / "test_file.txt"
    test_file.write_text("This is a test file.", encoding="utf-8")

    test_git_repo = Repo.init(str(test_repo_path))
    test_git_repo.index.add([str(test_file)])
    test_git_repo.index.commit("Initial test commit")

    result = get_git_history(str(test_repo_path), timedelta(weeks=1))

    assert result[0]["message"] == "Initial test commit"


# No git_repo key at all just means this project isn't tracking
# git history. That's fine, so it should come back None.
def test_resolve_git_repo_path_returns_none_when_missing():
    marker_file = {}
    result = resolve_git_repo_path(marker_file, "some/project/location")
    assert result is None


# git_repo written as a quoted empty string is one of the two
# ways someone can leave it blank. The program should stop.
def test_resolve_git_repo_path_exits_on_empty_string():
    marker_file = {"git_repo": ""}
    with pytest.raises(SystemExit):
        resolve_git_repo_path(marker_file, "some/project/location")


# git_repo written with nothing after the colon is the other way
# to leave it blank. YAML reads that as None, which is different
# from an empty string, so it needs its own check. The program
# should stop here too.
def test_resolve_git_repo_path_exits_on_none_value():
    marker_file = {"git_repo": None}
    with pytest.raises(SystemExit):
        resolve_git_repo_path(marker_file, "some/project/location")


# A real value should come back as the project location and the
# git_repo value joined together into one usable path.
def test_resolve_git_repo_path_returns_path_when_set(tmp_path):
    marker_file = {"git_repo": "code"}
    result = resolve_git_repo_path(marker_file, str(tmp_path))
    assert result == str(tmp_path / "code")
