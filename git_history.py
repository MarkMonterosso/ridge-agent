# ============================================================
# git_history.py
# Reads recent commit activity out of a project's code repo.
#
# get_git_history() only ever gets called once a project's
# ridge.yml has actually set git_repo, so if that path turns out
# to be wrong or isn't a real repo, that's a real misconfiguration
# — the program stops instead of quietly returning nothing and
# letting it look like the project just had no activity.
# ============================================================
import sys
from git import Repo
from datetime import datetime, timedelta
from git.exc import InvalidGitRepositoryError, NoSuchPathError

def get_git_history(repo_path, lookback: timedelta):

    history = []

    try:
        repo = Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError) as err:
        print(f"git_repo is set to '{repo_path}', but that path isn't a usable git repository: {err}")
        sys.exit(1)

    # How far back to look is worked out fresh, right here, every
    # time this function runs. lookback never gets turned into a
    # fixed date anywhere else and handed in — if it were, that
    # date would go stale the moment the config wasn't re-saved
    # for a while, and RIDGE is meant to keep running on its own.
    since: datetime = datetime.now() - lookback

    recent_commits = list(repo.iter_commits(since=since))

    if not recent_commits:
        # Not an error. A repo can easily go a week without a commit —
        # this just makes that visible instead of silent.
        print(f"[INF] No commits found in '{repo_path}' since {since.isoformat()}.")

    for commit in recent_commits:
        # Pull out only the plain values a field note will actually
        # need. Nothing from GitPython's own commit object leaves
        # this function.
        history.append({
            "commit_hash": commit.hexsha,
            "author": commit.author.name,
            "date": commit.committed_datetime.isoformat(),
            "message": commit.message.strip(),
            "files_changed": len(commit.stats.files)
    })

    return history
