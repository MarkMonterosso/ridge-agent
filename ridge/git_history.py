# ============================================================
# git_history.py
# Reads recent commit activity out of a project's code repo.
#
# resolve_git_repo_path() decides whether there's a repo to check.
# If ridge.yml has no git_repo line, the project doesn't track git
# history, and that's fine. If git_repo is there but blank, either
# empty or with nothing after the colon, someone started setting it
# up and didn't finish, so the program stops (ADR-0006).
#
# get_git_history() only runs once a real path is in hand. If that
# path is wrong or isn't a git repo, the program stops and says so.
# Returning an empty list would make it look like the project just
# had no commits that week.
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

    # Work out how far back to look right here, every time this
    # function runs (ADR-0005). If a fixed date were worked out
    # somewhere else and handed in, it would go stale as soon as the
    # config sat unchanged for a while, and RIDGE runs on its own.
    since: datetime = datetime.now().astimezone() - lookback

    recent_commits = list(repo.iter_commits(since=since))

    if not recent_commits:
        # Not an error. A repo can easily go a week without a commit.
        # This line makes that show up in the output.
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

    # A blank git_repo can show up two ways: an empty string in
    # quotes, or the key with nothing after the colon, which YAML
    # reads as None. Both mean the key was set up and left blank,
    # so both stop the program.
    if git_repo == "" or git_repo is None:
        print(
            f"Marker file '{project_location}/ridge.yml' contains an empty 'git_repo' key."
        )
        sys.exit(1)

    return str(os.path.join(project_location, git_repo))
