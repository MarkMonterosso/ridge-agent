# ============================================================
# test_git_history.py
# Tests for get_git_history in git_history.py.
#
# get_git_history is only ever called once git_repo has been
# confirmed present, so any failure reaching a real repo is a
# real misconfiguration — loud, not silently skipped. Both
# exceptions are tested with tmp_path, a fresh, empty, throwaway
# folder pytest hands each test, so these tests never touch a
# real repo and never go stale with real commit history.
# ============================================================
from datetime import timedelta
from git import Repo

import pytest

from git_history import get_git_history


# A path that exists but has no .git folder isn't a usable repo.
# Once git_repo is specified, that's a real misconfiguration —
# should exit loudly, not return an empty list quietly.
def test_get_git_history_exits_on_non_git_folder(tmp_path):
    with pytest.raises(SystemExit):
        get_git_history(str(tmp_path), timedelta(weeks=1))


# A path that doesn't exist at all is the same kind of failure —
# also a real misconfiguration, also loud.
def test_get_git_history_exits_on_missing_path(tmp_path):
    missing_path = tmp_path / "does_not_exist"
    with pytest.raises(SystemExit):
        get_git_history(str(missing_path), timedelta(weeks=1))


def test_get_git_history_returns_commits(tmp_path):
    # GitPython needs a real repo to work with, so make one. This
    # is a throwaway repo in a throwaway folder, so it doesn't matter that it's empty and has no commits yet.      
    test_repo_path = tmp_path / "test_repo"
    test_repo_path.mkdir()

    test_file = test_repo_path / "test_file.txt"
    test_file.write_text("This is a test file.", encoding="utf-8")

    test_git_repo = Repo.init(str(test_repo_path))
    test_git_repo.index.add([str(test_file)])   
    test_git_repo.index.commit("Initial test commit") 
    
    result = get_git_history(str(test_repo_path), timedelta(weeks=1))
    
    assert result[0]["message"] == "Initial test commit"