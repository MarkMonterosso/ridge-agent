# ============================================================
# change_index.py
# Builds the index RIDGE uses to tell what changed since the last
# post (ADR-0008).
#
# hash_file_text() turns a file's text into a short fingerprint.
# The same words always give the same fingerprint, so RIDGE can
# tell a real edit apart from a file whose timestamp changed while
# its text stayed the same.
#
# scan_project() looks through the folders a project's ridge.yml
# lists, and records an entry for every allowed file: its path
# relative to the project folder, its size, when it was last
# changed, and its fingerprint.
#
# index_path_for(), save_index() and load_index() keep the index
# in a JSON file between runs, so next week's scan has something
# to compare against. Each project gets its own file, named after
# its id. A save writes to a temporary file first and swaps it in
# only when the write has finished, so a crash halfway through
# leaves the old index as it was.
#
# Not built yet: comparing a scan to the saved index, and
# fingerprints for each paragraph.
# ============================================================

import json
import os
import sys
from hashlib import sha256
from pathlib import Path


def hash_file_text(file_path):
    # Windows and Linux end lines differently. Making them the same
    # first means a file only gets a new fingerprint when its words
    # change.
    text = file_path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n")  # Windows to Linux line endings

    return sha256(text.encode("utf-8")).hexdigest()[:16]  # 16 hex chars = 64 bits


def scan_project(project_location, conventions, included_patterns):
    # Returns one entry per allowed file, keyed by its path relative
    # to the project folder. The scan lists every allowed file,
    # broken ones included. Judging whether a file is a valid record
    # is records.py's job.
    index = {}

    for folder_path in conventions.values():
        folder = Path(project_location) / folder_path
        if not folder.exists():
            continue  # ADR-0006: a missing folder is normal for a new project

        matching = (
            set()
        )  # a set keeps one copy of each file, even if it matches two patterns

        for pattern in included_patterns:
            matching.update(
                folder.glob(pattern)
            )  # a pattern starting with **/ also reaches subfolders

        # Sorted, so the index comes out in the same order on every
        # computer, whatever order the operating system lists files in.
        for file_path in sorted(matching):
            relative_path = file_path.relative_to(
                project_location
            ).as_posix()  # forward slashes on every computer

            index[relative_path] = {
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime,
                "hash": hash_file_text(file_path),
            }
    return index


def index_path_for(state_folder, project_id):
    # Every project gets its own memory file, named after its id, so
    # a damaged file only ever affects one project.
    file_name = f"{project_id}-index.json"
    index_path = Path(state_folder) / file_name
    return index_path


def save_index(index, index_path):
    # Writes to a scratch copy first and swaps it in only when the
    # write has finished. If RIDGE crashes halfway through, only the
    # scratch copy is broken and the old index is still there.
    index_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = index_path.with_suffix(".tmp")

    with open(temp_path, "w", encoding="utf-8") as temp_file:
        json.dump(index, temp_file, indent=2)

    os.replace(temp_path, index_path)  # one step, so never half done


def load_index(index_path):
    # No file means this is the project's first run, so it returns
    # None. That is different from an empty index, which would make
    # every file look new. A damaged file stops the run for the same
    # reason: carrying on would post the whole project history.
    if not index_path.exists():
        return None  # no index yet, so nothing to compare against

    try:
        with open(index_path, "r", encoding="utf-8") as index_file:
            return json.load(index_file)
    except json.JSONDecodeError as error:
        print(f"[ERR] Error reading index file {index_path}: {error}", file=sys.stderr)
        sys.exit(1)
