# ============================================================
# git_history.py
# Reads recent commit activity out of a project's code repo.
#
# resolve_git_repo_path() decides whether there's even a repo to
# check. A project's ridge.yml might not set git_repo at all —
# that just means this project isn't tracking git history, nothing
# wrong with that. Or it might set git_repo but leave it blank,
# written either as an empty value or as just the key with nothing
# after the colon — that means someone set it up and left it
# unfinished, which is worth stopping the program for.
#
# get_git_history() only ever gets called once that's settled and
# a real path is in hand, so if that path turns out to be wrong or
# isn't a real repo, that's a real misconfiguration — the program
# stops instead of quietly returning nothing and letting it look
# like the project just had no activity.
# ============================================================
import os
import sys
from datetime import datetime, timedelta

from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError


def get_git_history(repo_path, lookback: timedelta):

    history = []

    try:
        repo = Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError) as err:
        print(
            f"git_repo is set to '{repo_path}', but that path isn't a usable git repository: {err}"
        )
        sys.exit(1)

    # How far back to look is worked out fresh, right here, every
    # time this function runs. lookback never gets turned into a
    # fixed date anywhere else and handed in — if it were, that
    # date would go stale the moment the config wasn't re-saved
    # for a while, and RIDGE is meant to keep running on its own.
    since: datetime = datetime.now()- lookback

    recent_commits = list(repo.iter_commits(since=since))

    if not recent_commits:
        # Not an error. A repo can easily go a week without a commit —
        # this just makes that visible instead of silent.
        print(f"[INF] No commits found in '{repo_path}' since {since.isoformat()}.")

    for commit in recent_commits:
        # Pull out only the plain values a field note will actually
        # need. Nothing from GitPython's own commit object leaves
        # this function.
        history.append(
            {
                "commit_hash": commit.hexsha,
                "author": commit.author.name,
                "date": commit.committed_datetime.isoformat(),
                "message": commit.message.strip(),
                "files_changed": len(commit.stats.files),
            }
        )

    return history


def resolve_git_repo_path(marker_file, project_location):

    if "git_repo" not in marker_file:
        return None
    else:
        git_repo = marker_file.get("git_repo")

    # A blank git_repo can show up two different ways: a quoted
    # empty string, or just the key with nothing after the colon,
    # which YAML reads in as None. Both mean the same thing — the
    # key was set up and left blank — so both have to stop the
    # program here, not just one of them.
    if git_repo == "" or git_repo is None:
        print(
            f"Marker file '{project_location}/ridge.yml' contains an empty 'git_repo' key."
        )
        sys.exit(1)

    return str(os.path.join(project_location, git_repo))
